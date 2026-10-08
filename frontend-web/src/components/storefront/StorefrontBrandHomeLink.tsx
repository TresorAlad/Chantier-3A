import { Link } from 'react-router-dom';
import { TDEV_LOGO_URL } from '@/components/brand/tdev-brand-assets';
import { cn } from '@/lib/utils';

type StorefrontBrandHomeLinkProps = {
  className?: string;
  /** En iframe partenaire : ouvre la billetterie dans un nouvel onglet. */
  embed?: boolean;
  imageClassName?: string;
};

/** Wordmark TDEV teinté rose (thème vitrine) → accueil billetterie. */
export function StorefrontBrandHomeLink({
  className,
  embed = false,
  imageClassName,
}: StorefrontBrandHomeLinkProps) {
  const img = (
    <img
      src={TDEV_LOGO_URL}
      alt="TDEV Festival - Accueil billetterie"
      className={cn('h-8 w-auto storefront-wordmark-rose sm:h-9', imageClassName)}
    />
  );

  if (embed) {
    return (
      <a
        href="/"
        target="_blank"
        rel="noopener noreferrer"
        className={cn(
          'inline-flex shrink-0 rounded-md transition-opacity hover:opacity-85 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
          className,
        )}
      >
        {img}
      </a>
    );
  }

  return (
    <Link
      to="/"
      className={cn(
        'inline-flex shrink-0 rounded-md transition-opacity hover:opacity-85 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
        className,
      )}
    >
      {img}
    </Link>
  );
}
