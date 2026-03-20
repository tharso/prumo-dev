on pad2(n)
	if n < 10 then
		return "0" & (n as text)
	end if
	return n as text
end pad2

on joinLines(itemsList)
	set AppleScript's text item delimiters to linefeed
	set joined to itemsList as text
	set AppleScript's text item delimiters to ""
	return joined
end joinLines

on cleanText(valueText)
	set normalized to valueText as text
	set AppleScript's text item delimiters to return
	set normalized to text items of normalized as text
	set AppleScript's text item delimiters to linefeed
	set normalized to text items of normalized as text
	set AppleScript's text item delimiters to tab
	set normalized to text items of normalized as text
	set AppleScript's text item delimiters to ""
	return normalized
end cleanText

on itemInList(targetText, candidates)
	repeat with oneItem in candidates
		if (oneItem as text) is targetText then
			return true
		end if
	end repeat
	return false
end itemInList

on reminderLabel(dueDate)
	if dueDate is missing value then
		return "dia inteiro"
	end if
	set hh to hours of dueDate
	set mm to minutes of dueDate
	if hh = 0 and mm = 0 then
		return "dia inteiro"
	end if
	return my pad2(hh) & ":" & my pad2(mm)
end reminderLabel

on run argv
	set action to "fetch"
	if (count of argv) > 0 then
		set action to item 1 of argv
	end if
	set observedLists to {}
	if (count of argv) > 1 then
		set idx to 2
		repeat while idx ≤ (count of argv)
			set currentArg to item idx of argv
			if currentArg is "--list" then
				if idx + 1 ≤ (count of argv) then
					set end of observedLists to item (idx + 1) of argv
					set idx to idx + 2
				else
					set idx to idx + 1
				end if
			else
				set idx to idx + 1
			end if
		end repeat
	end if
	set nowDate to current date
	set startOfDay to nowDate - (time of nowDate)
	set endOfDay to startOfDay + (1 * days)
	set outputLines to {}
	
	try
		tell application "Reminders"
			set allLists to lists
			set targetLists to {}
			if action is "auth" then
				set statusText to "connected"
			else
				set statusText to "ok"
			end if
			set end of outputLines to "STATUS:" & statusText
			set end of outputLines to "AUTHORIZATION:authorized"
			repeat with oneList in allLists
				set listName to (name of oneList as text)
				if (count of observedLists) is 0 or (my itemInList(listName, observedLists)) then
					set end of targetLists to oneList
					set end of outputLines to "LIST:" & listName
				end if
			end repeat
			
			if action is "fetch" then
				set foundAny to false
				repeat with oneList in targetLists
					set listName to (name of oneList as text)
					set openReminders to (every reminder of oneList whose completed is false)
					repeat with oneReminder in openReminders
						try
							set dueDate to due date of oneReminder
							if dueDate is not missing value then
								if dueDate ≥ startOfDay and dueDate < endOfDay then
									set foundAny to true
									set titleText to my cleanText(name of oneReminder as text)
									set safeListName to my cleanText(listName)
									set labelText to my reminderLabel(dueDate)
									set displayText to labelText & " | [Apple Reminders] " & titleText & " (" & safeListName & ")"
									set end of outputLines to "ITEM:" & titleText & tab & safeListName & tab & labelText & tab & displayText
								end if
							end if
						end try
					end repeat
				end repeat
				if foundAny is false then
					if (count of observedLists) > 0 then
						set end of outputLines to "NOTE:Nenhum Apple Reminder vencendo hoje nas listas observadas."
					else
						set end of outputLines to "NOTE:Nenhum Apple Reminder vencendo hoje."
					end if
				else
					if (count of observedLists) > 0 then
						set end of outputLines to "NOTE:Apple Reminders via AppleScript nas listas observadas."
					else
						set end of outputLines to "NOTE:Apple Reminders via AppleScript."
					end if
				end if
			end if
		end tell
	on error errMsg number errNum
		set outputLines to {"STATUS:error", "AUTHORIZATION:error", "ERROR:" & errNum & " | " & errMsg}
	end try
	
	return my joinLines(outputLines)
end run
