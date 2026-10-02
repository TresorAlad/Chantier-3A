import { registrationFormDisplayRows } from '@/lib/registration-form';
import type { Participant } from '../types';

const MARGIN = 14;
const LINE = 6;

function writeLines(pdf: { splitTextToSize: (t: string, w: number) => string[]; text: (t: string | string[], x: number, y: number) => void }, text: string, x: number, y: number, maxWidth: number): number {
  const lines = pdf.splitTextToSize(text, maxWidth);
  pdf.text(lines, x, y);
  return y + lines.length * LINE;
}

/** Export PDF : une section par inscrit, avec tous les champs du formulaire. */
export async function downloadParticipantsRegistrationPdf(
  participants: Participant[],
  filename = 'tdev_inscriptions',
): Promise<void> {
  if (!participants.length) {
    alert('Aucune inscription à exporter.');
    return;
  }

  const { jsPDF } = await import('jspdf');
  const pdf = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
  const pageWidth = pdf.internal.pageSize.getWidth();
  const pageHeight = pdf.internal.pageSize.getHeight();
  const maxWidth = pageWidth - MARGIN * 2;

  pdf.setFontSize(16);
  pdf.text('TDEV Festival 2026 - Formulaires participants', MARGIN, MARGIN + 4);
  pdf.setFontSize(10);
  pdf.setTextColor(100);
  pdf.text(`${participants.length} inscription(s) - ${new Date().toLocaleString('fr-FR')}`, MARGIN, MARGIN + 12);
  pdf.setTextColor(0);

  let y = MARGIN + 22;

  for (let index = 0; index < participants.length; index += 1) {
    const p = participants[index]!;
    if (index > 0) {
      pdf.addPage();
      y = MARGIN;
    }

    pdf.setFontSize(13);
    pdf.setFont('helvetica', 'bold');
    y = writeLines(pdf, p.name, MARGIN, y, maxWidth);
    pdf.setFont('helvetica', 'normal');
    pdf.setFontSize(10);
    y += 2;

    const meta = [
      `E-mail : ${p.email}`,
      `Pass : ${p.pass_name}`,
      `N° série : ${p.serial}`,
      `Statut : ${p.order_status}`,
    ];
    for (const line of meta) {
      if (y > pageHeight - MARGIN) {
        pdf.addPage();
        y = MARGIN;
      }
      y = writeLines(pdf, line, MARGIN, y, maxWidth);
    }

    y += 4;
    pdf.setFont('helvetica', 'bold');
    y = writeLines(pdf, 'Formulaire', MARGIN, y, maxWidth);
    pdf.setFont('helvetica', 'normal');
    y += 2;

    const rows = registrationFormDisplayRows(p.registration_form);
    if (!rows.length) {
      y = writeLines(pdf, 'Aucune réponse détaillée enregistrée (inscription antérieure au formulaire complet).', MARGIN, y, maxWidth);
    } else {
      for (const row of rows) {
        if (y > pageHeight - MARGIN - 10) {
          pdf.addPage();
          y = MARGIN;
        }
        pdf.setFont('helvetica', 'bold');
        y = writeLines(pdf, `${row.label}`, MARGIN, y, maxWidth);
        pdf.setFont('helvetica', 'normal');
        y = writeLines(pdf, row.value, MARGIN + 2, y, maxWidth - 2);
        y += 2;
      }
    }
  }

  pdf.save(`${filename}.pdf`);
}
