import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export default function AdminLogin() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-background">
            <div className="w-full max-w-md p-8 space-y-6 bg-card rounded-xl shadow-glow-primary border border-border/40">
                <div className="text-center">
                    <h1 className="text-2xl font-bold font-display text-foreground">Administration</h1>
                    <p className="text-muted-foreground text-sm mt-2">Connectez-vous pour accéder au dashboard</p>
                </div>
                <form className="space-y-4">
                    <div className="space-y-2">
                        <Label htmlFor="email">Email</Label>
                        <Input id="email" type="email" placeholder="admin@tdevfestival.com" />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="password">Mot de passe</Label>
                        <Input id="password" type="password" />
                    </div>
                    <Button type="submit" className="w-full shadow-glow-primary">Se connecter</Button>
                </form>
            </div>
        </div>
    );
}
