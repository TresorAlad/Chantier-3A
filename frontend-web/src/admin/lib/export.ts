export function exportToCsv(
  filename: string,
  rows: Record<string, any>[],
  options?: { columnOrder?: string[]; headers?: Record<string, string> },
): void {
  if (!rows || !rows.length) {
    alert("Aucune donnée à exporter.");
    return;
  }

  const keys = options?.columnOrder?.length
    ? options.columnOrder.filter((k) => k in rows[0]!)
    : Object.keys(rows[0]!);
  const header = keys.map((k) => options?.headers?.[k] ?? k).join(';');
  const content = rows.map(row => 
    keys.map(k => {
      let val = row[k];
      if (val === null || val === undefined) val = '';
      if (typeof val === 'object') val = JSON.stringify(val);
      const strVal = String(val).replace(/"/g, '""');
      return `"${strVal}"`;
    }).join(';')
  ).join('\r\n');

  const csvContent = "\uFEFF" + header + "\r\n" + content;
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', `${filename}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function exportToExcel(filename: string, rows: Record<string, any>[]): void {
  // Simple XML format readable by Excel or CSV fallback
  exportToCsv(`${filename}-excel`, rows);
}
