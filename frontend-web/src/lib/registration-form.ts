/**
 * Formulaire d'inscription participant - TDEV Festival 2026 (version PDF V1).
 * Les clés et valeurs correspondent exactement au schéma validé par l'API
 * (voir backend/orders/registration.py).
 */

export interface RegistrationFormValues {
    last_name: string;
    first_name: string;
    age_range: string;
    gender: string;
    country: string;
    city: string;
    phone: string;
    email: string;
    situation: string;
    activity_domain: string;
    school_program: string;
    digital_level: string;
    participation_reasons: string[];
    topics: string[];
    expectations: string;
    prior_participation: string;
    prior_liked: string;
    want_to_meet: string;
    discovery_channel: string;
    referred_by: string;
    stay_informed: string;
    preferred_channel: string;
    consent_data_processing: boolean;
    consent_marketing: boolean;
}

export type RegistrationFieldName = keyof RegistrationFormValues;
export type RegistrationFieldErrors = Partial<Record<RegistrationFieldName, string>>;

export interface ChoiceOption {
    value: string;
    label: string;
}

export const AGE_RANGE_OPTIONS: ChoiceOption[] = [
    { value: 'under_18', label: 'Moins de 18 ans' },
    { value: '18_24', label: '18 - 24 ans' },
    { value: '25_34', label: '25 - 34 ans' },
    { value: '35_plus', label: '35 ans et plus' },
];

export const GENDER_OPTIONS: ChoiceOption[] = [
    { value: 'woman', label: 'Femme' },
    { value: 'man', label: 'Homme' },
    { value: 'prefer_not', label: 'Préfère ne pas répondre' },
    { value: 'other', label: 'Autre' },
];

export const SITUATION_OPTIONS: ChoiceOption[] = [
    { value: 'student', label: 'Étudiant(e)' },
    { value: 'developer', label: 'Développeur ou ingénieur logiciel' },
    { value: 'entrepreneur', label: 'Entrepreneur(e)' },
    { value: 'digital_pro', label: 'Professionnel(le) du numérique' },
    { value: 'other_pro', label: "Professionnel(le) d'un autre secteur" },
    { value: 'researcher', label: 'Chercheur(euse) ou enseignant(e)' },
    { value: 'job_seeker', label: "Demandeur(se) d'emploi" },
    { value: 'content_creator', label: 'Créateur(trice) de contenu' },
    { value: 'other', label: 'Autre' },
];

export const DIGITAL_LEVEL_OPTIONS: ChoiceOption[] = [
    { value: 'beginner', label: 'Débutant(e)' },
    { value: 'learning', label: 'En apprentissage' },
    { value: 'intermediate', label: 'Intermédiaire' },
    { value: 'experienced', label: 'Expérimenté(e)' },
    { value: 'expert', label: 'Expert(e)' },
];

export const PARTICIPATION_REASON_OPTIONS: ChoiceOption[] = [
    { value: 'learn_skills', label: 'Apprendre et développer mes compétences' },
    { value: 'discover_digital', label: 'Découvrir les évolutions du numérique' },
    { value: 'understand_ai', label: "Mieux comprendre l'IA et ses enjeux" },
    { value: 'meet_professionals', label: 'Rencontrer des professionnels' },
    { value: 'grow_network', label: 'Développer mon réseau' },
    { value: 'find_opportunities', label: 'Découvrir des opportunités' },
    { value: 'present_projects', label: 'Présenter ou découvrir des projets' },
    { value: 'exchange_with_peers', label: "Échanger avec d'autres passionnés" },
    { value: 'other', label: 'Autre' },
];

export const TOPIC_OPTIONS: ChoiceOption[] = [
    { value: 'ai', label: 'Intelligence artificielle' },
    { value: 'software', label: 'Développement logiciel' },
    { value: 'cybersecurity', label: 'Cybersécurité' },
    { value: 'data', label: 'Data et data science' },
    { value: 'cloud', label: 'Cloud' },
    { value: 'open_source', label: 'Open source' },
    { value: 'entrepreneurship', label: 'Entrepreneuriat et innovation' },
    { value: 'fintech', label: 'FinTech' },
    { value: 'web_mobile', label: 'Web et mobile' },
    { value: 'digital_transformation', label: 'Transformation numérique' },
    { value: 'jobs', label: 'Emploi et métiers du numérique' },
    { value: 'ai_society', label: 'IA et société' },
    { value: 'other', label: 'Autre' },
];

export const PRIOR_PARTICIPATION_OPTIONS: ChoiceOption[] = [
    { value: 'yes_2024', label: 'Oui, en 2024' },
    { value: 'yes_other', label: "Oui, lors d'une autre édition" },
    { value: 'first_time', label: 'Non, ce sera ma première fois' },
];

export const DISCOVERY_CHANNEL_OPTIONS: ChoiceOption[] = [
    { value: 'facebook', label: 'Facebook' },
    { value: 'linkedin', label: 'LinkedIn' },
    { value: 'instagram', label: 'Instagram' },
    { value: 'whatsapp', label: 'WhatsApp' },
    { value: 'x', label: 'X' },
    { value: 'telegram', label: 'Telegram' },
    { value: 'website', label: 'Site web' },
    { value: 'friend', label: 'Un ami ou une connaissance' },
    { value: 'tech_community', label: 'Une communauté tech' },
    { value: 'school', label: 'Une école ou université' },
    { value: 'company', label: 'Une entreprise ou organisation' },
    { value: 'other', label: 'Autre' },
];

export const PREFERRED_CHANNEL_OPTIONS: ChoiceOption[] = [
    { value: 'whatsapp', label: 'WhatsApp' },
    { value: 'email', label: 'E-mail' },
    { value: 'telegram', label: 'Telegram' },
    { value: 'other', label: 'Autre' },
];

export const COUNTRY_OPTIONS: ChoiceOption[] = [
    'Togo',
    'Bénin',
    'Burkina Faso',
    "Côte d'Ivoire",
    'Ghana',
    'Niger',
    'Nigeria',
    'Sénégal',
    'Mali',
    'Cameroun',
    'Gabon',
    'Congo',
    'République démocratique du Congo',
    'Maroc',
    'Tunisie',
    'France',
    'Canada',
    'Belgique',
    'Autre pays',
].map((label) => ({ value: label, label }));

export const REGISTRATION_STEP_TITLES = [
    'Identité',
    'Coordonnées',
    'Votre profil',
    'Votre intérêt',
    'Expérience TDEV',
    'Découverte du festival',
    'Communauté',
    'Confirmation',
] as const;

export const REGISTRATION_STEP_COUNT = REGISTRATION_STEP_TITLES.length;

export function emptyRegistrationForm(): RegistrationFormValues {
    return {
        last_name: '',
        first_name: '',
        age_range: '',
        gender: '',
        country: '',
        city: '',
        phone: '',
        email: '',
        situation: '',
        activity_domain: '',
        school_program: '',
        digital_level: '',
        participation_reasons: [],
        topics: [],
        expectations: '',
        prior_participation: '',
        prior_liked: '',
        want_to_meet: '',
        discovery_channel: '',
        referred_by: '',
        stay_informed: '',
        preferred_channel: '',
        consent_data_processing: false,
        consent_marketing: false,
    };
}

const looksLikeEmail = (value: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());

/** Valide une étape (index 0 à 7) et renvoie les erreurs par champ. */
export function validateRegistrationStep(
    step: number,
    values: RegistrationFormValues,
): RegistrationFieldErrors {
    const errors: RegistrationFieldErrors = {};

    if (step === 0) {
        if (!values.last_name.trim()) errors.last_name = 'Indiquez votre nom.';
        if (!values.first_name.trim()) errors.first_name = 'Indiquez votre prénom.';
        if (!values.age_range) errors.age_range = "Choisissez votre tranche d'âge.";
        if (!values.country) errors.country = 'Choisissez votre pays de résidence.';
        if (!values.city.trim()) errors.city = 'Indiquez votre ville de résidence.';
    }

    if (step === 1) {
        if (!values.phone.trim()) errors.phone = 'Indiquez votre numéro de téléphone ou WhatsApp.';
        if (!values.email.trim()) errors.email = 'Indiquez votre adresse e-mail.';
        else if (!looksLikeEmail(values.email)) errors.email = 'Adresse e-mail invalide.';
    }

    if (step === 2) {
        if (!values.situation) errors.situation = 'Choisissez votre situation actuelle.';
        if (!values.activity_domain.trim()) {
            errors.activity_domain = "Indiquez votre domaine d'activité ou d'étude.";
        }
        if (!values.digital_level) {
            errors.digital_level = 'Choisissez votre niveau par rapport au numérique.';
        }
    }

    if (step === 3) {
        if (values.participation_reasons.length === 0) {
            errors.participation_reasons = 'Sélectionnez au moins une raison.';
        }
        if (values.topics.length === 0) errors.topics = 'Sélectionnez au moins un sujet.';
        if (!values.expectations.trim()) errors.expectations = 'Décrivez vos attentes.';
    }

    if (step === 4) {
        if (!values.prior_participation) {
            errors.prior_participation = 'Indiquez si vous avez déjà participé.';
        }
    }

    if (step === 5) {
        if (!values.discovery_channel) {
            errors.discovery_channel = 'Indiquez comment vous avez découvert le festival.';
        }
    }

    if (step === 6) {
        if (!values.stay_informed) {
            errors.stay_informed = 'Indiquez si vous souhaitez être informé(e).';
        }
        if (values.stay_informed === 'yes' && !values.preferred_channel) {
            errors.preferred_channel = 'Choisissez votre canal préféré.';
        }
    }

    if (step === 7) {
        if (!values.consent_data_processing) {
            errors.consent_data_processing = "Votre accord est requis pour finaliser l'inscription.";
        }
    }

    return errors;
}

/** Première étape contenant une erreur, ou -1 si le formulaire est complet. */
export function firstInvalidRegistrationStep(values: RegistrationFormValues): number {
    for (let step = 0; step < REGISTRATION_STEP_COUNT; step += 1) {
        if (Object.keys(validateRegistrationStep(step, values)).length > 0) return step;
    }
    return -1;
}

/** Charge utile envoyée à l'API (buyer.form). */
export function toRegistrationFormPayload(values: RegistrationFormValues) {
    return {
        last_name: values.last_name.trim(),
        first_name: values.first_name.trim(),
        age_range: values.age_range,
        gender: values.gender,
        country: values.country.trim(),
        city: values.city.trim(),
        phone: values.phone.trim(),
        email: values.email.trim().toLowerCase(),
        situation: values.situation,
        activity_domain: values.activity_domain.trim(),
        school_program: values.school_program.trim(),
        digital_level: values.digital_level,
        participation_reasons: values.participation_reasons,
        topics: values.topics,
        expectations: values.expectations.trim(),
        prior_participation: values.prior_participation,
        prior_liked: values.prior_liked.trim(),
        want_to_meet: values.want_to_meet.trim(),
        discovery_channel: values.discovery_channel,
        referred_by: values.referred_by.trim(),
        stay_informed: values.stay_informed === 'yes',
        preferred_channel: values.preferred_channel,
        consent_data_processing: values.consent_data_processing,
        consent_marketing: values.consent_marketing,
    };
}

const DRAFT_KEY = 'tdev_registration_draft';

/** Sauvegarde le brouillon de session (reprise après rafraîchissement). */
export function saveRegistrationDraft(values: RegistrationFormValues, step: number): void {
    try {
        sessionStorage.setItem(DRAFT_KEY, JSON.stringify({ values, step }));
    } catch {
        /* quota ou mode privé : le brouillon est optionnel */
    }
}

export function loadRegistrationDraft(): { values: RegistrationFormValues; step: number } | null {
    try {
        const raw = sessionStorage.getItem(DRAFT_KEY);
        if (!raw) return null;
        const parsed = JSON.parse(raw) as { values?: unknown; step?: unknown };
        if (!parsed.values || typeof parsed.values !== 'object') return null;
        return {
            values: { ...emptyRegistrationForm(), ...(parsed.values as RegistrationFormValues) },
            step: typeof parsed.step === 'number' ? parsed.step : 0,
        };
    } catch {
        return null;
    }
}

export function clearRegistrationDraft(): void {
    try {
        sessionStorage.removeItem(DRAFT_KEY);
    } catch {
        /* rien à nettoyer */
    }
}

/** Libellé lisible d'une valeur de choix (exports et récapitulatif). */
export function labelForChoice(options: ChoiceOption[], value: string): string {
    return options.find((option) => option.value === value)?.label ?? value;
}

export function labelsForChoices(options: ChoiceOption[], values: string[]): string[] {
    return values.map((value) => labelForChoice(options, value));
}

/** Lignes libellé / valeur pour fiche admin et export PDF. */
export function registrationFormDisplayRows(form: Record<string, unknown>): Array<{ label: string; value: string }> {
    const reasons = Array.isArray(form.participation_reasons)
        ? (form.participation_reasons as string[])
        : [];
    const topics = Array.isArray(form.topics) ? (form.topics as string[]) : [];
    const stay = form.stay_informed;
    const stayLabel =
        stay === true || stay === 'yes' ? 'Oui' : stay === false || stay === 'no' ? 'Non' : '';

    return [
        { label: 'Nom', value: String(form.last_name ?? '') },
        { label: 'Prénom', value: String(form.first_name ?? '') },
        { label: "Tranche d'âge", value: labelForChoice(AGE_RANGE_OPTIONS, String(form.age_range ?? '')) },
        { label: 'Genre', value: labelForChoice(GENDER_OPTIONS, String(form.gender ?? '')) },
        { label: 'Pays', value: String(form.country ?? '') },
        { label: 'Ville', value: String(form.city ?? '') },
        { label: 'Téléphone', value: String(form.phone ?? '') },
        { label: 'E-mail', value: String(form.email ?? '') },
        { label: 'Situation', value: labelForChoice(SITUATION_OPTIONS, String(form.situation ?? '')) },
        { label: "Domaine d'activité", value: String(form.activity_domain ?? '') },
        { label: 'Établissement', value: String(form.school_program ?? '') },
        { label: 'Niveau numérique', value: labelForChoice(DIGITAL_LEVEL_OPTIONS, String(form.digital_level ?? '')) },
        {
            label: 'Motivations',
            value: labelsForChoices(PARTICIPATION_REASON_OPTIONS, reasons).join(', '),
        },
        { label: 'Sujets', value: labelsForChoices(TOPIC_OPTIONS, topics).join(', ') },
        { label: 'Attentes', value: String(form.expectations ?? '') },
        {
            label: 'Participation antérieure',
            value: labelForChoice(PRIOR_PARTICIPATION_OPTIONS, String(form.prior_participation ?? '')),
        },
        { label: 'Apprécié lors des éditions passées', value: String(form.prior_liked ?? '') },
        { label: 'Profils à rencontrer', value: String(form.want_to_meet ?? '') },
        {
            label: 'Découverte du festival',
            value: labelForChoice(DISCOVERY_CHANNEL_OPTIONS, String(form.discovery_channel ?? '')),
        },
        { label: 'Recommandation', value: String(form.referred_by ?? '') },
        { label: 'Restez informé(e)', value: stayLabel },
        {
            label: 'Canal préféré',
            value: labelForChoice(PREFERRED_CHANNEL_OPTIONS, String(form.preferred_channel ?? '')),
        },
        {
            label: 'Consentement données',
            value: form.consent_data_processing ? 'Oui' : 'Non',
        },
        {
            label: 'Consentement marketing',
            value: form.consent_marketing ? 'Oui' : 'Non',
        },
    ].filter((row) => row.value.trim() !== '');
}

/** Colonnes CSV (clé interne -> en-tête français). */
export const REGISTRATION_CSV_HEADERS: Record<string, string> = {
    nom: 'Nom',
    prenom: 'Prénom',
    email: 'E-mail',
    telephone: 'Téléphone',
    ville: 'Ville',
    pays: 'Pays',
    pass: 'Type de pass',
    numeros_serie: 'Numéros de série',
    statut_commande: 'Statut commande',
    tranche_age: "Tranche d'âge",
    genre: 'Genre',
    situation: 'Situation',
    domaine: "Domaine d'activité",
    etablissement: 'Établissement',
    niveau_numerique: 'Niveau numérique',
    motivations: 'Motivations',
    sujets: 'Sujets',
    attentes: 'Attentes',
    participation_anterieure: 'Participation antérieure',
    appreciation_editions: 'Appréciation éditions passées',
    profils_rencontrer: 'Profils à rencontrer',
    decouverte_festival: 'Découverte du festival',
    recommandation: 'Recommandation',
    reste_informe: 'Reste informé(e)',
    canal_prefere: 'Canal préféré',
    consentement_donnees: 'Consentement données',
    consentement_marketing: 'Consentement marketing',
};

export function registrationRowForCsv(params: {
    form: Record<string, unknown>;
    passLabel: string;
    serials: string;
    orderStatus: string;
    fallbackName: string;
    fallbackEmail: string;
}): Record<string, string> {
    const { form, passLabel, serials, orderStatus, fallbackName, fallbackEmail } = params;
    const reasons = Array.isArray(form.participation_reasons)
        ? (form.participation_reasons as string[])
        : [];
    const topics = Array.isArray(form.topics) ? (form.topics as string[]) : [];
    const stay = form.stay_informed;
    const stayLabel =
        stay === true || stay === 'yes' ? 'Oui' : stay === false || stay === 'no' ? 'Non' : '';

    const firstName = String(form.first_name ?? '').trim();
    const lastName = String(form.last_name ?? '').trim();
    const email = String(form.email ?? fallbackEmail).trim();

    return {
        nom: lastName || fallbackName.split(' ').slice(1).join(' ') || fallbackName,
        prenom: firstName || fallbackName.split(' ')[0] || '',
        email,
        telephone: String(form.phone ?? ''),
        ville: String(form.city ?? ''),
        pays: String(form.country ?? ''),
        pass: passLabel,
        numeros_serie: serials,
        statut_commande: orderStatus,
        tranche_age: labelForChoice(AGE_RANGE_OPTIONS, String(form.age_range ?? '')),
        genre: labelForChoice(GENDER_OPTIONS, String(form.gender ?? '')),
        situation: labelForChoice(SITUATION_OPTIONS, String(form.situation ?? '')),
        domaine: String(form.activity_domain ?? ''),
        etablissement: String(form.school_program ?? ''),
        niveau_numerique: labelForChoice(DIGITAL_LEVEL_OPTIONS, String(form.digital_level ?? '')),
        motivations: labelsForChoices(PARTICIPATION_REASON_OPTIONS, reasons).join(', '),
        sujets: labelsForChoices(TOPIC_OPTIONS, topics).join(', '),
        attentes: String(form.expectations ?? ''),
        participation_anterieure: labelForChoice(
            PRIOR_PARTICIPATION_OPTIONS,
            String(form.prior_participation ?? ''),
        ),
        appreciation_editions: String(form.prior_liked ?? ''),
        profils_rencontrer: String(form.want_to_meet ?? ''),
        decouverte_festival: labelForChoice(DISCOVERY_CHANNEL_OPTIONS, String(form.discovery_channel ?? '')),
        recommandation: String(form.referred_by ?? ''),
        reste_informe: stayLabel,
        canal_prefere: labelForChoice(PREFERRED_CHANNEL_OPTIONS, String(form.preferred_channel ?? '')),
        consentement_donnees: form.consent_data_processing ? 'Oui' : 'Non',
        consentement_marketing: form.consent_marketing ? 'Oui' : 'Non',
    };
}
