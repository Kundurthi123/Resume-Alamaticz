import * as XLSX from 'xlsx';

/**
 * Exports JSON data to an Excel file (.xlsx)
 * @param {Array} data - Array of objects to export
 * @param {string} filename - Name of the file to save
 * @param {string} sheetName - Name of the worksheet
 */
export const exportToExcel = (data, filename = 'candidates.xlsx', sheetName = 'Candidates') => {
    if (!data || data.length === 0) {
        console.error('No data to export');
        return;
    }

    // Create a new workbook and worksheet
    const worksheet = XLSX.utils.json_to_sheet(data);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, sheetName);

    // Write file
    XLSX.writeFile(workbook, filename);
};

/**
 * Formats candidate data for Excel export by removing internal IDs and formatting Arrays
 * @param {Array} candidates - Raw candidate objects from API
 * @returns {Array} - Formatted objects for Excel
 */
export const formatCandidatesForExcel = (candidates, columns = []) => {
    return candidates.map(c => {
        const row = {};
        
        if (columns && columns.length > 0) {
            // Use dynamic columns provided from API
            columns.forEach(col => {
                row[col.col_label] = c[col.col_key] || (col.col_key === 'pega_experience' || col.col_key === 'total_experience' ? 0 : '—');
            });
            row['Filename'] = c.filename || '—';
            row['Analyzed At'] = c.timestamp ? new Date(c.timestamp).toLocaleString() : '—';
        } else {
            // Fallback to static if no dynamic columns
            row['Full Name'] = c.full_name || '—';
            row['Total Experience (yrs)'] = c.total_experience || 0;
            row['Pega Experience (yrs)'] = c.pega_experience || 0;
            row['Skills'] = c.skills || '—';
            row['Certifications'] = c.certifications || '—';
            row['CTC'] = c.ctc || '—';
            row['Notice Period'] = c.notice_period || '—';
            row['Current Organization'] = c.current_organization || '—';
            row['Email'] = c.email || '—';
            row['Phone'] = c.phone || '—';
            row['LinkedIn'] = c.linkedin || '—';
            row['Filename'] = c.filename || '—';
            row['Analyzed At'] = c.timestamp ? new Date(c.timestamp).toLocaleString() : '—';
        }
        
        return row;
    });
};
