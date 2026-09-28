import type { Options } from 'html2canvas';

const CAPTURE_OPTIONS: Partial<Options> = {
    scale: 2,
    backgroundColor: '#0a0a0a',
    useCORS: true,
    logging: false,
    imageTimeout: 15_000,
};

async function captureElement(element: HTMLElement): Promise<HTMLCanvasElement> {
    const html2canvas = (await import('html2canvas')).default;
    return html2canvas(element, CAPTURE_OPTIONS);
}

/** Capture le billet tel qu'affiché (pixel-perfect) en PNG. */
export async function downloadElementAsPng(element: HTMLElement, filename: string): Promise<void> {
    const canvas = await captureElement(element);
    const safeName = filename.endsWith('.png') ? filename : `${filename}.png`;
    const link = document.createElement('a');
    link.download = safeName;
    link.href = canvas.toDataURL('image/png');
    link.click();
}

/** Même rendu que l'écran : billet rasterisé puis inséré dans un PDF A4. */
export async function downloadElementAsPdf(element: HTMLElement, filename: string): Promise<void> {
    const canvas = await captureElement(element);
    const { jsPDF } = await import('jspdf');
    const imgData = canvas.toDataURL('image/png');
    const pdf = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
    const margin = 14;
    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();
    const maxW = pageWidth - margin * 2;
    const maxH = pageHeight - margin * 2;
    let w = maxW;
    let h = (canvas.height * w) / canvas.width;
    if (h > maxH) {
        h = maxH;
        w = (canvas.width * h) / canvas.height;
    }
    const x = (pageWidth - w) / 2;
    const y = (pageHeight - h) / 2;
    pdf.addImage(imgData, 'PNG', x, y, w, h);
    const safeName = filename.endsWith('.pdf') ? filename : `${filename}.pdf`;
    pdf.save(safeName);
}
