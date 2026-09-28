import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Money } from '@/components/ui/money';
import { scaleIn, scrollRevealViewport, transitionMedium } from '@/components/motion/motion-presets';
import MediaSlot from '@/components/brand/media-slot';
import { cn } from '@/lib/utils';

export interface ProductCardProps {
    name: string;
    description?: string;
    priceMinor: number;
    currency: string;
    soldOut?: boolean;
    onAdd: () => void;
    index?: number;
    imageSrc?: string | null;
}

const ProductCard = ({ name, description, priceMinor, currency, soldOut = false, onAdd, index = 0, imageSrc = null }: ProductCardProps) => {
    const reduce = useReducedMotion();
    return (
        <motion.div
            initial={reduce ? false : 'hidden'}
            viewport={scrollRevealViewport}
            transition={{ ...transitionMedium, delay: index * 0.05 }}
            {...(reduce
                ? {}
                : {
                      whileInView: 'visible',
                      variants: scaleIn,
                      ...(soldOut ? {} : { whileHover: { y: -4 } }),
                  })}
            className="h-full"
        >
            <Card elevation="elevated" className={cn('overflow-hidden', soldOut && 'opacity-65')}>
                <MediaSlot
                    aspect="square"
                    tint="pink"
                    src={imageSrc}
                    alt={name}
                    {...(imageSrc ? {} : { caption: name })}
                    className="rounded-none border-0 shadow-none"
                    interactive={false}
                />
                <CardHeader>
                    <CardTitle className="text-lg">{name}</CardTitle>
                    {description ? <CardDescription>{description}</CardDescription> : null}
                </CardHeader>
                <CardContent className="flex-1">
                    <p className="font-display text-2xl font-bold tracking-tight">
                        <Money minor={priceMinor} currency={currency} />
                    </p>
                    {soldOut ? <p className="mt-2 text-sm font-semibold text-destructive">Épuisé</p> : null}
                </CardContent>
                <CardFooter>
                    <Button className="w-full" variant="outline" size="lg" disabled={soldOut} onClick={onAdd}>
                        <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
                        Ajouter au panier
                    </Button>
                </CardFooter>
            </Card>
        </motion.div>
    );
};

export default ProductCard;
