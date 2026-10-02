import React, { useState } from 'react';
import {
  Settings,
  Shield,
  Key,
  Database,
  CheckCircle2,
  AlertTriangle,
  Save,
  Server,
} from 'lucide-react';
import { PageHeader } from '../components/ui/PageHeader';
import { useToast } from '../context/ToastContext';
import { USE_MOCKS, API_URL } from '../services/api';

export const SettingsPage: React.FC = () => {
  const { success } = useToast();
  const [activeTab, setActiveTab] = useState<'general' | 'security' | 'api'>('general');

  // Form states
  const [orgName, setOrgName] = useState('TDEV Community Association');
  const [currency, setCurrency] = useState('XOF');
  const [contactEmail, setContactEmail] = useState('support@tdev.bj');
  const [useMocks, setUseMocks] = useState(USE_MOCKS);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    success('Paramètres enregistrés', 'Vos modifications ont été prises en compte.');
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Paramètres de la Plateforme & Sécurité"
        subtitle="Configuration globale, sécurité cryptographique et intégration backend FastAPI"
      />

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-2 text-xs font-semibold">
        <button
          onClick={() => setActiveTab('general')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-all ${
            activeTab === 'general'
              ? 'bg-violet-600 text-white shadow-sm'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <Settings className="w-4 h-4" />
          Paramètres Généraux
        </button>

        <button
          onClick={() => setActiveTab('security')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-all ${
            activeTab === 'security'
              ? 'bg-violet-600 text-white shadow-sm'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <Shield className="w-4 h-4" />
          Sécurité & Chiffrement
        </button>

        <button
          onClick={() => setActiveTab('api')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-all ${
            activeTab === 'api'
              ? 'bg-violet-600 text-white shadow-sm'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <Server className="w-4 h-4" />
          Connexion API & Neon DB
        </button>
      </div>

      {activeTab === 'general' && (
        <form onSubmit={handleSave} className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm max-w-2xl space-y-5 text-xs sm:text-sm">
          <div>
            <label className="block font-bold text-slate-700 mb-1.5">
              Nom de l'Organisation
            </label>
            <input
              type="text"
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 transition-all font-medium text-slate-800"
            />
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1.5">
              Devise par Défaut
            </label>
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 transition-all font-medium text-slate-800"
            >
              <option value="XOF">XOF (Franc CFA BCEAO)</option>
              <option value="USD">USD (Dollar Américain)</option>
              <option value="EUR">EUR (Euro)</option>
              <option value="ZAR">ZAR (Rand Sud-Africain)</option>
            </select>
          </div>

          <div>
            <label className="block font-bold text-slate-700 mb-1.5">
              Email de Contact / Assistance
            </label>
            <input
              type="email"
              value={contactEmail}
              onChange={(e) => setContactEmail(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 transition-all font-medium text-slate-800"
            />
          </div>

          <button
            type="submit"
            className="flex items-center gap-2 px-5 py-2.5 bg-violet-600 hover:bg-violet-700 text-white rounded-xl font-bold shadow-md shadow-violet-600/20 transition-all"
          >
            <Save className="w-4 h-4" />
            Enregistrer les Modifications
          </button>
        </form>
      )}

      {activeTab === 'security' && (
        <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm max-w-2xl space-y-6">
          <div className="flex items-start gap-4 p-4 rounded-xl bg-emerald-50 border border-emerald-100 text-emerald-800">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
            <div className="text-xs leading-relaxed">
              <strong className="block text-sm font-bold text-emerald-900 mb-0.5">
                Isolation Stricte Côté Frontend (Conformité Section 34)
              </strong>
              Toutes les données sensibles (`password_hash`, `private_key`, `key_vault`, `sealed_keys`)
              sont strictement confinées au backend FastAPI et ne sont jamais renvoyées dans le navigateur.
            </div>
          </div>

          <div className="space-y-4 text-xs">
            <h4 className="font-bold text-slate-900 text-sm">Gestion des Clés Cryptographiques</h4>
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-100 space-y-2">
              <div className="flex justify-between">
                <span className="text-slate-500">Algorithme de signature</span>
                <span className="font-mono font-bold text-slate-800">Ed25519 (RFC 8032)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Protection Key Vault</span>
                <span className="font-bold text-emerald-600">Actif (Table key_vault scellée)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Authentification Session</span>
                <span className="font-mono text-slate-700">Token Hash SHA-256</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'api' && (
        <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm max-w-2xl space-y-6">
          <div className="space-y-3 text-xs">
            <h4 className="font-bold text-slate-900 text-sm">Configuration de l’Accès Backend</h4>
            
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-100 space-y-2">
              <div className="flex justify-between">
                <span className="text-slate-500">URL API Configurée</span>
                <span className="font-mono font-bold text-violet-700">{API_URL}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Mode d’accès actuel</span>
                <span className={`font-bold ${useMocks ? 'text-amber-600' : 'text-emerald-600'}`}>
                  {useMocks ? 'Données Mockées (VITE_USE_MOCKS=true)' : 'Direct FastAPI / Neon DB'}
                </span>
              </div>
            </div>

            <p className="text-slate-500 leading-relaxed">
              Pour connecter définitivement ce dashboard à votre serveur FastAPI :
              éditez le fichier <code className="px-1.5 py-0.5 bg-slate-100 rounded text-violet-600 font-mono">.env</code> et définissez :
            </p>

            <pre className="p-3 bg-slate-900 text-slate-200 rounded-xl font-mono text-xs overflow-x-auto">
              VITE_API_URL=http://localhost:8088/api{'\n'}
              VITE_USE_MOCKS=false
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};
