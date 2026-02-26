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
export const formatCandidatesForExcel = (candidates) => {
    return candidates.map(c => ({
        'Full Name': c.full_name || '—',
        'Total Experience (yrs)': c.total_experience || 0,
        'Pega Experience (yrs)': c.pega_experience || 0,
        'Skills': c.skills || '—',
        'Certifications': c.certifications || '—',
        'CTC': c.ctc || '—',
        'Notice Period': c.notice_period || '—',
        'Current Organization': c.current_organization || '—',
        'Email': c.email || '—',
        'Phone': c.phone || '—',
        'LinkedIn': c.linkedin || '—',
        'Filename': c.filename || '—',
        'Analyzed At': c.timestamp ? new Date(c.timestamp).toLocaleString() : '—'
    }));
};
