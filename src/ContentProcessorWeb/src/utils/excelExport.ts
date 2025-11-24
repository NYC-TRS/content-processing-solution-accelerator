import * as XLSX from 'xlsx';

interface ProcessedDocument {
  processed_file_name: string;
  processed_file_mime_type: string;
  imported_time: string;
  status: string;
  processed_time: string;
  entity_score: number;
  schema_score: number;
  process_id: string;
  last_modified_by: string;
}

/**
 * Converts process time from HH:MM:SS format to decimal seconds
 */
const convertProcessTimeToSeconds = (time: string): number => {
  if (!time || time === '...') return 0;

  const parts = time.split(':');
  if (parts.length === 3) {
    const hours = parseInt(parts[0], 10) || 0;
    const minutes = parseInt(parts[1], 10) || 0;
    const seconds = parseFloat(parts[2]) || 0;
    return hours * 3600 + minutes * 60 + seconds;
  }
  return 0;
};

/**
 * Formats entity score as percentage
 */
const formatScore = (score: number): string => {
  if (score === null || score === undefined) return 'N/A';
  return `${(score * 100).toFixed(2)}%`;
};

/**
 * Formats schema score, showing "Verified" if user-modified
 */
const formatSchemaScore = (score: number, lastModifiedBy: string): string => {
  if (lastModifiedBy === 'user') return 'Verified';
  if (score === null || score === undefined) return 'N/A';
  return `${(score * 100).toFixed(2)}%`;
};

/**
 * Exports processed documents data to an Excel file
 * @param data Array of processed documents from the grid
 * @param fileName Optional custom file name (defaults to "ProcessedDocuments.xlsx")
 */
export const exportToExcel = (data: ProcessedDocument[], fileName: string = 'ProcessedDocuments.xlsx'): void => {
  if (!data || data.length === 0) {
    console.warn('No data to export');
    return;
  }

  // Transform data into Excel-friendly format
  const excelData = data.map((item) => ({
    'File Name': item.processed_file_name || '',
    'File Type': item.processed_file_mime_type || '',
    'Imported Date': item.imported_time || '',
    'Status': item.status || '',
    'Process Time (seconds)': convertProcessTimeToSeconds(item.processed_time),
    'Entity Score': formatScore(item.entity_score),
    'Schema Score': formatSchemaScore(item.schema_score, item.last_modified_by),
    'Process ID': item.process_id || '',
    'Last Modified By': item.last_modified_by || 'system',
  }));

  // Create a new workbook and worksheet
  const worksheet = XLSX.utils.json_to_sheet(excelData);

  // Set column widths for better readability
  const columnWidths = [
    { wch: 30 }, // File Name
    { wch: 20 }, // File Type
    { wch: 20 }, // Imported Date
    { wch: 15 }, // Status
    { wch: 20 }, // Process Time
    { wch: 15 }, // Entity Score
    { wch: 15 }, // Schema Score
    { wch: 40 }, // Process ID
    { wch: 20 }, // Last Modified By
  ];
  worksheet['!cols'] = columnWidths;

  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, 'Processed Documents');

  // Generate Excel file and trigger download
  XLSX.writeFile(workbook, fileName);
};

/**
 * Exports detailed extraction results to Excel
 * @param result The extracted JSON result from a processed document
 * @param fileName The file name for the export
 */
export const exportDetailedResultsToExcel = (result: any, fileName: string): void => {
  if (!result) {
    console.warn('No result data to export');
    return;
  }

  // Flatten the result object into key-value pairs
  const flattenObject = (obj: any, prefix: string = ''): any[] => {
    const flattened: any[] = [];

    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        const value = obj[key];
        const newKey = prefix ? `${prefix}.${key}` : key;

        if (value && typeof value === 'object' && !Array.isArray(value)) {
          flattened.push(...flattenObject(value, newKey));
        } else if (Array.isArray(value)) {
          flattened.push({
            'Field': newKey,
            'Value': JSON.stringify(value)
          });
        } else {
          flattened.push({
            'Field': newKey,
            'Value': value !== null && value !== undefined ? String(value) : ''
          });
        }
      }
    }

    return flattened;
  };

  const excelData = flattenObject(result);

  // Create worksheet and workbook
  const worksheet = XLSX.utils.json_to_sheet(excelData);
  worksheet['!cols'] = [{ wch: 40 }, { wch: 60 }];

  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, 'Extracted Results');

  // Generate Excel file and trigger download
  XLSX.writeFile(workbook, fileName);
};

/**
 * Exports bulk extraction results for multiple documents to a single Excel file on one sheet
 * All documents are rows with their extracted fields as columns
 * @param documents Array of documents with their extraction results
 * @param fileName The file name for the export
 */
export const exportBulkResultsToExcel = (documents: Array<{ fileName: string, result: any }>, fileName: string = 'BulkExtractionResults.xlsx'): void => {
  if (!documents || documents.length === 0) {
    console.warn('No documents to export');
    return;
  }

  // Flatten nested objects into dot notation (e.g., address.street)
  const flattenObject = (obj: any, prefix: string = ''): any => {
    const flattened: any = {};

    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        const value = obj[key];
        const newKey = prefix ? `${prefix}.${key}` : key;

        if (value && typeof value === 'object' && !Array.isArray(value)) {
          Object.assign(flattened, flattenObject(value, newKey));
        } else if (Array.isArray(value)) {
          flattened[newKey] = JSON.stringify(value);
        } else {
          flattened[newKey] = value !== null && value !== undefined ? value : '';
        }
      }
    }

    return flattened;
  };

  // Collect all unique field names across all documents
  const allFields = new Set<string>();
  const flattenedDocuments = documents.map(doc => {
    if (!doc.result) return null;
    const flattened = flattenObject(doc.result);
    Object.keys(flattened).forEach(key => allFields.add(key));
    return {
      'Document Name': doc.fileName,
      ...flattened
    };
  }).filter(doc => doc !== null);

  if (flattenedDocuments.length === 0) {
    console.warn('No valid documents to export');
    return;
  }

  // Create worksheet with all documents on one sheet
  const worksheet = XLSX.utils.json_to_sheet(flattenedDocuments);

  // Set column widths
  const columnCount = Object.keys(flattenedDocuments[0]).length;
  worksheet['!cols'] = Array(columnCount).fill({ wch: 20 });
  // Make Document Name column wider
  worksheet['!cols'][0] = { wch: 35 };

  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, 'All Results');

  // Generate Excel file and trigger download
  XLSX.writeFile(workbook, fileName);
};
