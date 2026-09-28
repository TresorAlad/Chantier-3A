import { orders as ordersApi } from '@/lib/api';

export async function downloadGuestTicketPdf(params: {
    orderId: string;
    email: string;
    ticketId: string;
    serial: string;
}): Promise<void> {
    const url = ordersApi.guestTicketPdfUrl(params.orderId, params.email, params.ticketId);
    const res = await fetch(url, { credentials: 'include' });
    if (!res.ok) {
        let detail = 'Impossible de générer le PDF du billet.';
        try {
            const body = (await res.json()) as { error?: { message?: string } };
            if (body.error?.message) detail = body.error.message;
        } catch {
            /* réponse non JSON (ex. route absente → HTML) */
        }
        throw new Error(detail);
    }
    const contentType = res.headers.get('content-type') ?? '';
    if (!contentType.includes('pdf')) {
        throw new Error('Réponse invalide du serveur (PDF attendu). Redémarrez l’API billetterie.');
    }
    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = objectUrl;
    link.download = `billet-${params.serial}.pdf`;
    link.click();
    URL.revokeObjectURL(objectUrl);
}
