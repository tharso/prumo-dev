const CONFIG = {
  expectedAccount: 'PERSONAL_ACCOUNT_EMAIL',
  rootFolderName: 'Prumo',
  snapshotsFolderName: 'snapshots',
  snapshotFileName: 'email-snapshot.json',
  defaultLookbackHours: 24,
  searchBatchSize: 100,
  version: '1.0'
};

function runSnapshot(since) {
  const account = resolveAccount_();
  validateExpectedAccount_(account);

  const sinceDate = parseSince_(since);
  const snapshot = {
    version: CONFIG.version,
    account: account || CONFIG.expectedAccount,
    generated_at: toIsoString_(new Date()),
    since: toIsoString_(sinceDate),
    emails: [],
    calendar: {
      today: [],
      tomorrow: []
    }
  };

  try {
    snapshot.emails = loadEmails_(sinceDate, snapshot.account);
  } catch (error) {
    snapshot.emails_error = formatError_(error);
    logError_('Gmail snapshot failed', error);
  }

  try {
    snapshot.calendar = loadCalendar_();
  } catch (error) {
    snapshot.calendar = { today: [], tomorrow: [] };
    snapshot.calendar_error = formatError_(error);
    logError_('Calendar snapshot failed', error);
  }

  const file = saveSnapshotToDrive_(snapshot);

  return {
    ok: !snapshot.emails_error && !snapshot.calendar_error,
    file_id: file.getId(),
    file_name: file.getName(),
    account: snapshot.account,
    generated_at: snapshot.generated_at
  };
}

function installOrRefreshTrigger() {
  removeTriggersForHandler_('runSnapshot');

  ScriptApp.newTrigger('runSnapshot')
    .timeBased()
    .everyMinutes(15)
    .create();
}

function removeSnapshotTriggers() {
  removeTriggersForHandler_('runSnapshot');
}

function loadEmails_(sinceDate, account) {
  const queryDate = Utilities.formatDate(
    sinceDate,
    Session.getScriptTimeZone(),
    'yyyy/MM/dd'
  );
  const query = 'in:anywhere after:' + queryDate + ' -in:drafts';
  const selfAddresses = buildSelfAddressSet_(account);
  const emailsById = {};
  let start = 0;

  while (true) {
    const threads = GmailApp.search(query, start, CONFIG.searchBatchSize);

    if (!threads.length) {
      break;
    }

    for (let i = 0; i < threads.length; i += 1) {
      const messages = threads[i].getMessages();

      for (let j = 0; j < messages.length; j += 1) {
        const message = messages[j];

        if (message.isDraft()) {
          continue;
        }

        if (message.getDate().getTime() < sinceDate.getTime()) {
          continue;
        }

        if (!isIncomingMessage_(message, selfAddresses)) {
          continue;
        }

        emailsById[message.getId()] = buildEmailSnapshot_(message);
      }
    }

    start += threads.length;

    if (threads.length < CONFIG.searchBatchSize) {
      break;
    }
  }

  return Object.keys(emailsById)
    .map(function mapEmail(id) {
      return emailsById[id];
    })
    .sort(function sortByNewest(a, b) {
      return new Date(b.date).getTime() - new Date(a.date).getTime();
    });
}

function loadCalendar_() {
  const calendar = CalendarApp.getDefaultCalendar();
  const today = new Date();
  const tomorrow = new Date(today.getTime());

  tomorrow.setDate(tomorrow.getDate() + 1);

  return {
    today: buildEventSnapshots_(calendar.getEventsForDay(today)),
    tomorrow: buildEventSnapshots_(calendar.getEventsForDay(tomorrow))
  };
}

function buildEventSnapshots_(events) {
  return events
    .map(function mapEvent(event) {
      return {
        title: event.getTitle(),
        start: toIsoString_(event.getStartTime()),
        end: toIsoString_(event.getEndTime()),
        location: resolveEventLocation_(event),
        attendees_count: getAttendeesCount_(event)
      };
    })
    .sort(function sortByStart(a, b) {
      return new Date(a.start).getTime() - new Date(b.start).getTime();
    });
}

function buildEmailSnapshot_(message) {
  const plainBody = safeGetPlainBody_(message);
  const labels = message.getThread().getLabels().map(function mapLabel(label) {
    return label.getName();
  });

  return {
    id: message.getId(),
    from: message.getFrom(),
    subject: message.getSubject(),
    date: toIsoString_(message.getDate()),
    snippet: buildSnippet_(plainBody),
    labels: labels,
    has_attachments: message.getAttachments({
      includeAttachments: true,
      includeInlineImages: false
    }).length > 0
  };
}

function saveSnapshotToDrive_(snapshot) {
  const rootFolder = DriveApp.getRootFolder();
  const prumoFolder = findOrCreateFolder_(rootFolder, CONFIG.rootFolderName);
  const snapshotsFolder = findOrCreateFolder_(prumoFolder, CONFIG.snapshotsFolderName);
  const content = JSON.stringify(snapshot, null, 2);
  const existingFiles = snapshotsFolder.getFilesByName(CONFIG.snapshotFileName);

  if (existingFiles.hasNext()) {
    const file = existingFiles.next();
    file.setContent(content);
    return file;
  }

  return snapshotsFolder.createFile(
    CONFIG.snapshotFileName,
    content,
    MimeType.PLAIN_TEXT
  );
}

function findOrCreateFolder_(parentFolder, folderName) {
  const folders = parentFolder.getFoldersByName(folderName);

  if (folders.hasNext()) {
    return folders.next();
  }

  return parentFolder.createFolder(folderName);
}

function parseSince_(since) {
  if (!since) {
    return new Date(Date.now() - (CONFIG.defaultLookbackHours * 60 * 60 * 1000));
  }

  if (since instanceof Date) {
    return since;
  }

  if (typeof since === 'number') {
    return new Date(since);
  }

  if (typeof since === 'string') {
    const parsed = new Date(since);

    if (!isNaN(parsed.getTime())) {
      return parsed;
    }
  }

  throw new Error(
    'Invalid "since" value. Use ISO-8601, Date, or epoch milliseconds.'
  );
}

function resolveAccount_() {
  const effectiveEmail = Session.getEffectiveUser().getEmail();

  if (effectiveEmail) {
    return effectiveEmail;
  }

  const activeEmail = Session.getActiveUser().getEmail();

  if (activeEmail) {
    return activeEmail;
  }

  return CONFIG.expectedAccount;
}

function validateExpectedAccount_(detectedAccount) {
  if (!detectedAccount) {
    return;
  }

  if (detectedAccount.toLowerCase() !== CONFIG.expectedAccount.toLowerCase()) {
    throw new Error(
      'This script expects ' + CONFIG.expectedAccount + ' but is running as ' + detectedAccount + '.'
    );
  }
}

function buildSelfAddressSet_(account) {
  const addresses = {};
  const aliases = GmailApp.getAliases();
  const knownAddresses = [CONFIG.expectedAccount, account].concat(aliases);

  for (let i = 0; i < knownAddresses.length; i += 1) {
    const value = normalizeEmail_(knownAddresses[i]);

    if (value) {
      addresses[value] = true;
    }
  }

  return addresses;
}

function isIncomingMessage_(message, selfAddresses) {
  const fromHeader = message.getFrom();
  const emails = extractEmails_(fromHeader);

  if (!emails.length) {
    return true;
  }

  for (let i = 0; i < emails.length; i += 1) {
    if (selfAddresses[emails[i]]) {
      return false;
    }
  }

  return true;
}

function extractEmails_(value) {
  const matches = String(value || '')
    .toLowerCase()
    .match(/[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}/g);

  return matches || [];
}

function normalizeEmail_(value) {
  const emails = extractEmails_(value);
  return emails.length ? emails[0] : String(value || '').trim().toLowerCase();
}

function safeGetPlainBody_(message) {
  const plainBody = message.getPlainBody();

  if (plainBody) {
    return plainBody;
  }

  return stripHtml_(message.getBody());
}

function buildSnippet_(value) {
  const normalized = String(value || '')
    .replace(/\s+/g, ' ')
    .trim();

  if (!normalized) {
    return '';
  }

  return normalized.length <= 200
    ? normalized
    : normalized.slice(0, 200).trim() + '...';
}

function stripHtml_(value) {
  return String(value || '')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>');
}

function resolveEventLocation_(event) {
  const location = String(event.getLocation() || '').trim();

  if (location) {
    return location;
  }

  const description = String(event.getDescription() || '');
  const urlMatch = description.match(/https?:\/\/\S+/i);

  return urlMatch ? urlMatch[0] : '';
}

function getAttendeesCount_(event) {
  try {
    return event.getGuestList().length;
  } catch (error) {
    logError_('Could not count attendees for event "' + event.getTitle() + '"', error);
    return 0;
  }
}

function toIsoString_(date) {
  const timeZone = Session.getScriptTimeZone();
  const base = Utilities.formatDate(date, timeZone, "yyyy-MM-dd'T'HH:mm:ss");
  const offset = Utilities.formatDate(date, timeZone, 'Z');

  return base + offset.slice(0, 3) + ':' + offset.slice(3);
}

function removeTriggersForHandler_(handlerName) {
  const triggers = ScriptApp.getProjectTriggers();

  for (let i = 0; i < triggers.length; i += 1) {
    if (triggers[i].getHandlerFunction() === handlerName) {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }
}

function formatError_(error) {
  if (!error) {
    return 'Unknown error';
  }

  if (error.message) {
    return error.message;
  }

  return String(error);
}

function logError_(prefix, error) {
  const message = prefix + ': ' + formatError_(error);
  const stack = error && error.stack ? '\n' + error.stack : '';

  console.error(message + stack);
  Logger.log(message + stack);
}
