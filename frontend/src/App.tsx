import { useEffect, useState, type FormEvent } from 'react';
import { Loader2, Calendar, MapPin, Moon, Sun, Check, Gift } from 'lucide-react';
import { motion } from 'framer-motion';
import { useTheme } from '@/components/theme-provider';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { ApiError } from '@/lib/api';
import type { FestivalEvent } from '@/lib/api-types';
import { loadBilletterieStorefront, type BilletterieProduct } from '@/lib/billetterie-storefront';
import {
    completeCheckout,
    validateRegistration,
    type RegistrationInput,
} from '@/lib/billetterie-checkout';

const emptyForm = (): RegistrationInput => ({
    first_name: '',
    last_name: '',
    email: '',
    motivation: '',
    wish: '',
    school_name: '',
});

export default function App() {
    const [event, setEvent] = useState<FestivalEvent | null>(null);
    const [products, setProducts] = useState<BilletterieProduct[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const { theme, setTheme } = useTheme();

    const [registerOpen, setRegisterOpen] = useState(false);
    const [activeProduct, setActiveProduct] = useState<BilletterieProduct | null>(null);
    const [form, setForm] = useState(emptyForm);
    const [fieldErrors, setFieldErrors] = useState<Partial<Record<keyof RegistrationInput, string>>>({});
    const [submitting, setSubmitting] = useState(false);

    const [successOpen, setSuccessOpen] = useState(false);
    const [successTitle, setSuccessTitle] = useState('');
    const [successBody, setSuccessBody] = useState('');

    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const data = await loadBilletterieStorefront();
                if (cancelled) return;
                setEvent(data.event);
                setProducts(data.products);
            } catch (err) {
                if (cancelled) return;
                const message =
                    err instanceof ApiError
                        ? err.message
                        : err instanceof Error
                          ? err.message
                          : 'Erreur lors du chargement des billets.';
                setError(message);
            } finally {
                if (!cancelled) setLoading(false);
            }
        })();
        return () => {
            cancelled = true;
        };
    }, []);

    const openRegistration = (product: BilletterieProduct) => {
        setActiveProduct(product);
        setForm(emptyForm());
        setFieldErrors({});
        setRegisterOpen(true);
    };

    const showSuccess = (title: string, body: string) => {
        setSuccessTitle(title);
        setSuccessBody(body);
        setSuccessOpen(true);
    };

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        if (!event || !activeProduct || activeProduct.externalUrl) return;

        const nextErrors = validateRegistration(form, activeProduct.ticketType);
        setFieldErrors(nextErrors);
        if (Object.keys(nextErrors).length > 0) return;

        setSubmitting(true);
        try {
            const outcome = await completeCheckout({
                eventId: event.id,
                ticketType: activeProduct.ticketType,
                registration: form,
            });
            setRegisterOpen(false);

            if (outcome.kind === 'free_confirmed') {
                showSuccess(
                    'Inscription réussie',
                    `Merci ! Votre inscription au ${activeProduct.title} est confirmée. Vous recevrez votre billet par e-mail à ${outcome.email} dans quelques instants. Pensez à vérifier vos spams.`,
                );
                return;
            }

            if (outcome.redirectUrl) {
                showSuccess(
                    'Paiement sécurisé',
                    `Après validation de votre paiement pour le ${activeProduct.title}, vous recevrez votre billet par e-mail à ${outcome.email}.`,
                );
                window.setTimeout(() => {
                    window.location.href = outcome.redirectUrl!;
                }, 1200);
                return;
            }

            showSuccess(
                'Commande enregistrée',
                `Une fois le paiement confirmé, votre billet ${activeProduct.title} vous sera envoyé par e-mail à ${outcome.email}.`,
            );
        } catch (err) {
            const message =
                err instanceof ApiError
                    ? err.message
                    : 'Impossible de finaliser pour le moment. Réessayez dans quelques instants.';
            setFieldErrors({ email: message });
        } finally {
            setSubmitting(false);
        }
    };

    const venue = event?.venue_name?.trim() || 'Lieu principal du festival';
    const isStudentPass = activeProduct?.ticketType.pass_tier === 'student';

    return (
        <div className="min-h-screen bg-background text-foreground transition-colors duration-300">
            <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/80 backdrop-blur-md supports-[backdrop-filter]:bg-background/60 shadow-soft">
                <div className="container flex h-16 items-center justify-between">
                    <div className="flex items-center gap-3">
                        <img src="/image.png" className="h-9 w-auto dark:invert transition-all" alt="T-Dev Logo" />
                        <div className="flex flex-col">
                            <span className="font-display font-extrabold text-lg tracking-tight text-foreground">
                                TDEV Festival
                            </span>
                            <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">
                                Billetterie officielle
                            </span>
                        </div>
                    </div>
                    <div className="flex items-center gap-3">
                        <Button
                            variant="ghost"
                            size="icon"
                            className="text-muted-foreground hover:text-foreground rounded-full"
                            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                            aria-label="Changer le thème"
                        >
                            {theme === 'dark' ? <Sun size={19} /> : <Moon size={19} />}
                        </Button>
                        <Button size="sm" className="shadow-glow-primary" asChild>
                            <a href="#passes">Réserver un billet</a>
                        </Button>
                    </div>
                </div>
            </header>

            <section className="relative overflow-hidden py-16 md:py-24 bg-gradient-to-b from-primary/5 via-transparent to-transparent">
                <div className="container relative z-10 text-center flex flex-col items-center">
                    <h1 className="text-4xl md:text-display-xl font-display font-black tracking-tight text-foreground max-w-4xl leading-tight">
                        Réservez vos tickets pour le{' '}
                        <span className="text-primary">{event?.title ?? 'TDEV Festival 2026'}</span>
                    </h1>
                    <p className="mt-4 text-lg md:text-xl text-muted-foreground max-w-2xl leading-relaxed">
                        Accédez aux conférences, aux ateliers, à la soirée Nexus Night et repartez avec le Welcome Pack
                        officiel.
                    </p>
                    <div className="mt-6 flex flex-wrap gap-6 text-sm text-muted-foreground justify-center">
                        <div className="flex items-center gap-2">
                            <Calendar className="h-4 w-4 text-primary" />
                            <span>Festival sur 2 jours</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <MapPin className="h-4 w-4 text-primary" />
                            <span>{venue}</span>
                        </div>
                    </div>
                </div>
            </section>

            <main id="passes" className="container py-10 pb-20">
                {loading ? (
                    <div className="flex justify-center items-center min-h-[300px]">
                        <Loader2 className="h-10 w-10 animate-spin text-primary" />
                    </div>
                ) : error ? (
                    <div className="bg-destructive/10 text-destructive p-4 rounded-lg text-center max-w-md mx-auto border border-destructive/20">
                        <p>{error}</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-stretch">
                        {products.map((ticket, index) => (
                            <motion.div
                                key={ticket.ticketType.id}
                                initial={{ opacity: 0, y: 25 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ duration: 0.45, delay: index * 0.12 }}
                                className="flex"
                            >
                                <Card
                                    className={`w-full flex flex-col overflow-hidden relative transition-all duration-300 hover:shadow-floating hover:-translate-y-1 ${
                                        ticket.popular
                                            ? 'border-2 border-primary shadow-glow-primary bg-card/90'
                                            : 'border-border/60 bg-card/60 hover:border-primary/40'
                                    }`}
                                >
                                    {ticket.badgeText && (
                                        <div className="absolute top-4 right-4 z-10">
                                            <Badge
                                                variant={ticket.popular ? 'default' : 'secondary'}
                                                className="font-semibold text-xs shadow-sm"
                                            >
                                                {ticket.badgeText}
                                            </Badge>
                                        </div>
                                    )}

                                    <div className="relative h-44 overflow-hidden bg-muted/50">
                                        <div className="absolute inset-0 bg-gradient-to-t from-card via-card/40 to-transparent" />
                                        <div className="absolute bottom-4 left-6 right-6">
                                            <span className="text-xs uppercase tracking-wider text-primary font-bold">
                                                {ticket.category}
                                            </span>
                                            <h3 className="font-display font-extrabold text-2xl text-foreground mt-0.5 leading-snug">
                                                {ticket.title}
                                            </h3>
                                            {ticket.subtitle && (
                                                <p className="text-sm text-muted-foreground mt-0.5">{ticket.subtitle}</p>
                                            )}
                                        </div>
                                    </div>

                                    <CardHeader className="pt-2 pb-4">
                                        <div className="flex items-baseline gap-2 mb-2">
                                            <span
                                                className={`font-display font-black text-3xl tracking-tight ${
                                                    ticket.isFree
                                                        ? 'text-emerald-500 dark:text-emerald-400'
                                                        : 'text-foreground'
                                                }`}
                                            >
                                                {ticket.priceLabel}
                                            </span>
                                        </div>
                                        <CardDescription className="text-sm leading-relaxed text-muted-foreground">
                                            {ticket.description}
                                        </CardDescription>
                                    </CardHeader>

                                    <CardContent className="mt-auto pt-2 pb-6 flex-grow">
                                        <div className="border-t border-border/40 pt-4">
                                            <p className="text-xs font-bold uppercase tracking-wider text-foreground/80 mb-3 flex items-center gap-1.5">
                                                <Gift className="h-3.5 w-3.5 text-primary" /> Ce qui est inclus :
                                            </p>
                                            <ul className="space-y-2.5 text-sm">
                                                {ticket.inclusions.map((item) => (
                                                    <li key={item} className="flex items-start gap-2.5">
                                                        <div className="mt-0.5 p-0.5 rounded-full bg-primary/10 text-primary shrink-0">
                                                            <Check className="h-3.5 w-3.5 stroke-[2.5]" />
                                                        </div>
                                                        <span className="text-foreground/90 font-medium leading-tight">
                                                            {item}
                                                        </span>
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    </CardContent>

                                    <CardFooter className="pt-4 pb-6 border-t border-border/40 bg-muted/20">
                                        {ticket.externalUrl ? (
                                            <Button
                                                variant="outline"
                                                className="w-full font-bold h-11"
                                                onClick={() => window.open(ticket.externalUrl, '_blank')}
                                            >
                                                Découvrir les goodies
                                            </Button>
                                        ) : (
                                            <Button
                                                variant={ticket.popular ? 'default' : 'outline'}
                                                className={`w-full font-bold h-11 ${
                                                    ticket.popular ? 'shadow-glow-primary' : ''
                                                }`}
                                                onClick={() => openRegistration(ticket)}
                                            >
                                                {ticket.isFree ? 'Réserver gratuitement' : 'Choisir ce pass'}
                                            </Button>
                                        )}
                                    </CardFooter>
                                </Card>
                            </motion.div>
                        ))}
                    </div>
                )}
            </main>

            <Dialog open={registerOpen} onOpenChange={setRegisterOpen}>
                <DialogContent className="sm:max-w-[480px] max-h-[90vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle>{activeProduct?.title ?? 'Inscription'}</DialogTitle>
                        <DialogDescription>
                            {activeProduct?.isFree
                                ? 'Complétez le formulaire pour recevoir votre pass par e-mail.'
                                : 'Après paiement, votre billet vous sera envoyé par e-mail.'}
                        </DialogDescription>
                    </DialogHeader>
                    <form className="space-y-4 py-2" onSubmit={handleSubmit}>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="firstName">Prénom</Label>
                                <Input
                                    id="firstName"
                                    value={form.first_name}
                                    onChange={(ev) => setForm({ ...form, first_name: ev.target.value })}
                                    required
                                />
                                {fieldErrors.first_name && (
                                    <p className="text-xs text-destructive">{fieldErrors.first_name}</p>
                                )}
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="lastName">Nom</Label>
                                <Input
                                    id="lastName"
                                    value={form.last_name}
                                    onChange={(ev) => setForm({ ...form, last_name: ev.target.value })}
                                    required
                                />
                                {fieldErrors.last_name && (
                                    <p className="text-xs text-destructive">{fieldErrors.last_name}</p>
                                )}
                            </div>
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="email">E-mail</Label>
                            <Input
                                id="email"
                                type="email"
                                value={form.email}
                                onChange={(ev) => setForm({ ...form, email: ev.target.value })}
                                required
                            />
                            {fieldErrors.email && <p className="text-xs text-destructive">{fieldErrors.email}</p>}
                        </div>
                        {isStudentPass && (
                            <div className="space-y-2">
                                <Label htmlFor="school">École ou organisation</Label>
                                <Input
                                    id="school"
                                    value={form.school_name ?? ''}
                                    onChange={(ev) => setForm({ ...form, school_name: ev.target.value })}
                                    required
                                />
                                {fieldErrors.school_name && (
                                    <p className="text-xs text-destructive">{fieldErrors.school_name}</p>
                                )}
                            </div>
                        )}
                        <div className="space-y-2">
                            <Label htmlFor="why">Pourquoi voulez-vous participer ?</Label>
                            <Textarea
                                id="why"
                                value={form.motivation}
                                onChange={(ev) => setForm({ ...form, motivation: ev.target.value })}
                                required
                            />
                            {fieldErrors.motivation && (
                                <p className="text-xs text-destructive">{fieldErrors.motivation}</p>
                            )}
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="expectations">Qu&apos;attendez-vous de l&apos;événement ?</Label>
                            <Textarea
                                id="expectations"
                                value={form.wish}
                                onChange={(ev) => setForm({ ...form, wish: ev.target.value })}
                                required
                            />
                            {fieldErrors.wish && <p className="text-xs text-destructive">{fieldErrors.wish}</p>}
                        </div>
                        <DialogFooter>
                            <Button type="submit" className="w-full" disabled={submitting}>
                                {submitting ? (
                                    <>
                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                        Envoi en cours…
                                    </>
                                ) : activeProduct?.isFree ? (
                                    'Valider l\'inscription'
                                ) : (
                                    'Continuer vers le paiement'
                                )}
                            </Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>

            <Dialog open={successOpen} onOpenChange={setSuccessOpen}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle>{successTitle}</DialogTitle>
                        <DialogDescription className="text-base leading-relaxed pt-2">{successBody}</DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button className="w-full" onClick={() => setSuccessOpen(false)}>
                            Fermer
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <footer className="border-t border-border/40 py-8 bg-muted/30 text-center text-sm text-muted-foreground">
                <div className="container flex flex-col sm:flex-row items-center justify-between gap-4">
                    <div className="flex items-center gap-2">
                        <img src="/image.png" className="h-6 w-auto dark:invert" alt="T-Dev Logo" />
                        <span>© 2026 TDEV Festival. Tous droits réservés.</span>
                    </div>
                </div>
            </footer>
        </div>
    );
}
