import EventKit
import Foundation

struct Output: Encodable {
    var strategy: String
    var status: String
    var authorization_status: String
    var lists: [String]
    var today: [[String: String]]
    var note: String?
    var error: String?
}

func authorizationStatusString() -> String {
    let status = EKEventStore.authorizationStatus(for: .reminder)
    if #available(macOS 14.0, *) {
        switch status {
        case .fullAccess:
            return "fullAccess"
        case .writeOnly:
            return "writeOnly"
        case .denied:
            return "denied"
        case .restricted:
            return "restricted"
        case .notDetermined:
            return "notDetermined"
        @unknown default:
            return "unknown"
        }
    } else {
        switch status {
        case .authorized:
            return "authorized"
        case .fullAccess:
            return "fullAccess"
        case .writeOnly:
            return "writeOnly"
        case .denied:
            return "denied"
        case .restricted:
            return "restricted"
        case .notDetermined:
            return "notDetermined"
        @unknown default:
            return "unknown"
        }
    }
}

func hasReminderAccess() -> Bool {
    let status = EKEventStore.authorizationStatus(for: .reminder)
    if #available(macOS 14.0, *) {
        return status == .fullAccess
    } else {
        return status == .authorized
    }
}

func emit(_ output: Output) {
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
    let data = try! encoder.encode(output)
    FileHandle.standardOutput.write(data)
}

func listTitles(from store: EKEventStore) -> [String] {
    store.calendars(for: .reminder).map { $0.title }.sorted()
}

func formatterFor(_ timezoneName: String) -> DateFormatter {
    let formatter = DateFormatter()
    formatter.locale = Locale(identifier: "pt_BR")
    formatter.timeZone = TimeZone(identifier: timezoneName) ?? .current
    formatter.dateFormat = "HH:mm"
    return formatter
}

func dayBounds(_ timezoneName: String) -> (Date, Date) {
    let tz = TimeZone(identifier: timezoneName) ?? .current
    var calendar = Calendar(identifier: .gregorian)
    calendar.timeZone = tz
    let now = Date()
    let start = calendar.startOfDay(for: now)
    let end = calendar.date(byAdding: .day, value: 1, to: start)!
    return (start, end)
}

func renderReminder(_ reminder: EKReminder, timezoneName: String) -> [String: String] {
    let title = reminder.title?.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty == false ? reminder.title! : "Lembrete sem título"
    let listTitle = reminder.calendar.title
    var label = "dia inteiro"
    if let due = reminder.dueDateComponents?.date {
        label = formatterFor(timezoneName).string(from: due)
    }
    return [
        "title": title,
        "list": listTitle,
        "label": label,
        "display": "\(label) | [Apple Reminders] \(title) (\(listTitle))"
    ]
}

func parseObservedLists(_ args: [String]) -> [String] {
    var observed: [String] = []
    var idx = 0
    while idx < args.count {
        if args[idx] == "--list", idx + 1 < args.count {
            let candidate = args[idx + 1].trimmingCharacters(in: .whitespacesAndNewlines)
            if !candidate.isEmpty {
                observed.append(candidate)
            }
            idx += 2
        } else {
            idx += 1
        }
    }
    return observed
}

func requestAccess(store: EKEventStore) -> Bool {
    let semaphore = DispatchSemaphore(value: 0)
    var granted = false
    var capturedError: Error?
    if #available(macOS 14.0, *) {
        store.requestFullAccessToReminders { ok, error in
            granted = ok
            capturedError = error
            semaphore.signal()
        }
    } else {
        store.requestAccess(to: .reminder) { ok, error in
            granted = ok
            capturedError = error
            semaphore.signal()
        }
    }
    _ = semaphore.wait(timeout: .now() + 30)
    if capturedError != nil {
        return false
    }
    return granted
}

func runAuth() {
    let store = EKEventStore()
    let initialStatus = authorizationStatusString()
    let granted: Bool
    if initialStatus == "notDetermined" {
        granted = requestAccess(store: store)
    } else {
        granted = hasReminderAccess()
    }
    let finalStatus = authorizationStatusString()
    let status = granted ? "connected" : "denied"
    emit(Output(strategy: "eventkit-local", status: status, authorization_status: finalStatus, lists: listTitles(from: store), today: [], note: nil, error: granted ? nil : "Apple negou ou não concedeu acesso aos Reminders."))
}

func runFetch(timezoneName: String, observedLists: [String]) {
    let store = EKEventStore()
    let authStatus = authorizationStatusString()
    guard hasReminderAccess() else {
        emit(Output(strategy: "eventkit-local", status: "disconnected", authorization_status: authStatus, lists: listTitles(from: store), today: [], note: nil, error: "Apple Reminders ainda não autorizados neste Mac."))
        return
    }
    let (start, end) = dayBounds(timezoneName)
    let calendars = store.calendars(for: .reminder)
    let selectedCalendars: [EKCalendar]
    if observedLists.isEmpty {
        selectedCalendars = calendars
    } else {
        let observedSet = Set(observedLists)
        selectedCalendars = calendars.filter { observedSet.contains($0.title) }
    }
    let visibleTitles = selectedCalendars.map { $0.title }.sorted()
    let predicate = store.predicateForIncompleteReminders(withDueDateStarting: start, ending: end, calendars: selectedCalendars.isEmpty ? nil : selectedCalendars)
    let semaphore = DispatchSemaphore(value: 0)
    var rendered: [[String: String]] = []
    store.fetchReminders(matching: predicate) { reminders in
        let items = reminders ?? []
        rendered = items.map { renderReminder($0, timezoneName: timezoneName) }
        semaphore.signal()
    }
    _ = semaphore.wait(timeout: .now() + 30)
    let note: String
    if rendered.isEmpty {
        note = observedLists.isEmpty ? "Nenhum Apple Reminder vencendo hoje." : "Nenhum Apple Reminder vencendo hoje nas listas observadas."
    } else {
        note = observedLists.isEmpty ? "Apple Reminders via EventKit." : "Apple Reminders via EventKit nas listas observadas."
    }
    emit(Output(strategy: "eventkit-local", status: "ok", authorization_status: authStatus, lists: visibleTitles, today: rendered, note: note, error: nil))
}

let args = CommandLine.arguments
let action = args.dropFirst().first ?? "fetch"
var timezoneName = "America/Sao_Paulo"
let observedLists = parseObservedLists(Array(args.dropFirst()))
if let idx = args.firstIndex(of: "--timezone"), args.indices.contains(idx + 1) {
    timezoneName = args[idx + 1]
}

switch action {
case "auth":
    runAuth()
case "fetch":
    runFetch(timezoneName: timezoneName, observedLists: observedLists)
default:
    emit(Output(strategy: "eventkit-local", status: "error", authorization_status: authorizationStatusString(), lists: [], today: [], note: nil, error: "acao desconhecida"))
}
