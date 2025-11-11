// --- 1. CONFIGURATION ---
// PASTE YOUR DEPLOYED FASTAPI SERVER URL HERE
// It must end with /audit-doc
const API_ENDPOINT = ""; // <-- CHANGE THIS

// --- 2. ADD CUSTOM MENU ON OPEN ---
function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu('🤖 MCQ Auditor')
    .addItem('Audit Doc from Active Cell', 'runAuditFromActiveCell')
    .addToUi();
}

// --- 3. MAIN AUDIT FUNCTION (FIXED) ---
function runAuditFromActiveCell() {
  var ui = SpreadsheetApp.getUi();
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var cell = sheet.getActiveCell();
  
  // Get the URL from the active cell
  var docUrl = cell.getValue();
  
  if (!docUrl || !docUrl.includes("docs.google.com")) {
    ui.alert("Invalid Input", "Please select a cell that contains a valid Google Doc URL.", ui.ButtonSet.OK);
    return;
  }
  
  // --- FIX: Using SpreadsheetApp ---
  SpreadsheetApp.getActiveSpreadsheet().toast('🚀 Starting audit... This may take a minute.', 'Status');

  try {
    // --- 4. PREPARE THE API REQUEST ---
    var payload = {
      doc_url: docUrl
    };
    
    var options = {
      'method': 'post',
      'contentType': 'application/json',
      'payload': JSON.stringify(payload),
      'muteHttpExceptions': true // IMPORTANT: to catch errors
    };

    // --- 5. CALL THE FASTAPI SERVER ---
    var response = UrlFetchApp.fetch(API_ENDPOINT, options);
    var responseCode = response.getResponseCode();
    var responseBody = response.getContentText();
    
    if (responseCode === 200) {
      // Success! Parse the JSON
      var results = JSON.parse(responseBody);
      
      if (results.length === 0) {
        ui.alert("No results found. Check the document format.");
        return;
      }
      
      // --- 6. WRITE RESULTS TO THE SHEET ---
      // Pass 'docUrl' to the helper function
      writeResultsToSheet(sheet, cell, results, docUrl); 
      
      // --- FIX: Using SpreadsheetApp ---
      SpreadsheetApp.getActiveSpreadsheet().toast('✅ Audit complete! Results loaded.', 'Success', 5);
      
    } else {
      // Handle server errors (404, 500, etc.)
      var errorMsg = `Error ${responseCode}: ${responseBody}`;
      console.error(errorMsg);
      ui.alert('Audit Failed', `The server returned an error: ${errorMsg}. \n\nCheck the server logs.`, ui.ButtonSet.OK);
    }
    
  } catch (e) {
    // Handle script errors (e.g., network timeout)
    console.error(e);
    ui.alert('Script Error', `An error occurred: ${e.message}`, ui.ButtonSet.OK);
  }
}

/**
 * --- 7. HELPER FUNCTION ---
 * Helper function to write the JSON results to the sheet.
 * This version creates a full header row and places data below it.
 */
function writeResultsToSheet(sheet, sourceCell, results, docUrl) {
  var startRow = sourceCell.getRow();    // e.g., 2
  var startCol = sourceCell.getColumn(); // e.g., 1 (Column A)
  
  // Headers now include 'Document Link'
  var headers = ['Document Link', 'Q. No', 'Status', 'Issue Summary'];
  
  // Write headers starting from the source cell (e.g., A2:D2)
  sheet.getRange(startRow, startCol, 1, headers.length).setValues([headers]).setFontWeight('bold');
  
  // Prepare Data with URL prepended to each row
  var data = results.map(function(item) {
    return [
      docUrl, // Prepend the URL to each result row
      item.Q_no,
      item['Option Status'],
      item['Issue Summary']
    ];
  });

  if (data.length === 0) {
    return;
  }
  
  // Write all data starting on the *next* row (e.g., A3:D(3+n))
  var dataRange = sheet.getRange(startRow + 1, startCol, data.length, data[0].length);
  dataRange.setValues(data);
  
  // Auto-resize all columns in the new table
  sheet.autoResizeColumns(startCol, headers.length);


  // --- 🎨 NEW: ADD COLOR FORMATTING ---
  
  // Define the column index for 'Status' (Header: A, B, C -> Col C is 'Status')
  var statusColIndex = startCol + 2; // (A=1 + 2 = 3, which is Column C)
  
  // Create arrays for background and font colors
  var backgroundColors = [];
  var fontColors = [];

  // Loop through the data we just prepared
  data.forEach(function(row) {
    var status = row[2]; // Get the status string from our data array
    
    if (status === "OK") {
      backgroundColors.push(["#c9ead4"]); // Soft green background
      fontColors.push(["#096024"]);     // Dark green text
    } else if (status === "Faulty") {
      backgroundColors.push(["#f4c7c3"]); // Soft red background
      fontColors.push(["#990000"]);     // Dark red text
    } else {
      backgroundColors.push([null]);      // Default background
      fontColors.push([null]);          // Default text color
    }
  });

  // Apply the colors to the Status column in a single batch
  var statusRange = sheet.getRange(startRow + 1, statusColIndex, data.length, 1);
  statusRange.setBackgrounds(backgroundColors);
  statusRange.setFontColors(fontColors);
}
