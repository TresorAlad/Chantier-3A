import { orders as ordersApi } from '@/lib/api';

/**
 * Récupère les billets invités puis déclenche un téléchargement PDF par billet.
 * Le pass Nexus donne aussi accès au festival : la commande contient alors deux billets.
 */
export async function downloadGuestTicketPdfForOrder(orderId: string, email: string): Promise<void> {
    const data = await ordersApi.getGuest(orderId, email.trim());
    const tickets = (data.tickets ?? []).filter((ticket) => ticket?.id && ticket.serial);
    if (tickets.length === 0) {
        throw new Error(
            'Votre billet n\'est pas encore disponible. Réessayez dans un instant ou consultez vos e-mails.',
        );
    }
    for (const ticket of tickets) {
        await downloadGuestTicketPdf({
            orderId,
            email: email.trim(),
            ticketId: ticket.id,
            serial: ticket.serial,
        });
    }
}

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
