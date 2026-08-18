import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Copy, Check, QrCode, Share2, Clock, ShieldCheck, Sparkles } from 'lucide-react';
import { toast } from 'sonner';

interface ConviteModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  inviteData: {
    token: string;
    invite_url: string;
    role: string;
    expira_em: string;
  } | null;
}

export const ConviteModal: React.FC<ConviteModalProps> = ({ open, onOpenChange, inviteData }) => {
  const [copied, setCopied] = useState(false);

  if (!inviteData) return null;

  const qrCodeUrl = `https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=${encodeURIComponent(inviteData.invite_url)}`;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(inviteData.invite_url);
      setCopied(true);
      toast.success('Link do convite copiado para a área de transferência!');
      setTimeout(() => setCopied(false), 3000);
    } catch {
      toast.error('Não foi possível copiar o link.');
    }
  };

  const handleWhatsAppShare = () => {
    const text = encodeURIComponent(
      `🔒 *Convite para Acesso Administrativo - App Jornada*\n\nVocê foi convidado para se cadastrar como *${inviteData.role}* no sistema.\n\nAcesse o link abaixo para concluir seu cadastro (válido por 24 horas):\n${inviteData.invite_url}`
    );
    window.open(`https://wa.me/?text=${text}`, '_blank');
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md bg-slate-900 text-slate-100 border-slate-800 shadow-2xl">
        <DialogHeader className="space-y-2 text-center sm:text-left">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-xl bg-primary/10 text-primary border border-primary/20">
                <Sparkles size={20} className="animate-pulse" />
              </div>
              <DialogTitle className="text-xl font-bold text-white">Convite Gerado com Sucesso</DialogTitle>
            </div>
            <Badge variant="outline" className="bg-amber-500/10 text-amber-400 border-amber-500/30 gap-1 text-xs py-1">
              <Clock size={12} /> Válido por 24h
            </Badge>
          </div>
          <DialogDescription className="text-slate-400 text-xs">
            Compartilhe o QR Code ou o link seguro abaixo para que o novo {inviteData.role.toLowerCase()} conclua o cadastro.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col items-center justify-center py-4 space-y-4">
          {/* QR Code Container */}
          <div className="relative group p-4 bg-white rounded-2xl shadow-xl border-4 border-slate-800 transition-all transform hover:scale-[1.02]">
            <img
              src={qrCodeUrl}
              alt="QR Code de Convite"
              className="w-48 h-48 rounded-lg object-contain"
            />
            <div className="absolute inset-0 bg-slate-900/10 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center pointer-events-none">
              <span className="bg-slate-900/90 text-white text-[10px] px-2 py-1 rounded-md font-medium shadow-md">
                Escaneie com a câmera
              </span>
            </div>
          </div>

          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <ShieldCheck size={14} className="text-emerald-400" />
            <span>Papel atribuído: <strong className="text-emerald-400 uppercase font-semibold">{inviteData.role}</strong></span>
          </div>

          {/* Campo de Link */}
          <div className="w-full space-y-2">
            <Label className="text-xs text-slate-300">Link Seguro de Cadastro</Label>
            <div className="flex gap-2">
              <Input
                readOnly
                value={inviteData.invite_url}
                className="bg-slate-950/80 border-slate-800 text-xs font-mono text-slate-300 select-all focus-visible:ring-primary/40"
              />
              <Button
                type="button"
                variant={copied ? 'default' : 'secondary'}
                onClick={handleCopy}
                className="shrink-0 gap-1.5 text-xs font-semibold"
              >
                {copied ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
                {copied ? 'Copiado' : 'Copiar'}
              </Button>
            </div>
          </div>
        </div>

        {/* Ações Inferiores */}
        <div className="flex flex-col sm:flex-row gap-2 pt-2 border-t border-slate-800/80">
          <Button
            type="button"
            className="w-full bg-emerald-600 hover:bg-emerald-500 text-white gap-2 font-semibold text-xs"
            onClick={handleWhatsAppShare}
          >
            <Share2 size={15} />
            Compartilhar no WhatsApp
          </Button>
          <Button
            type="button"
            variant="outline"
            className="w-full sm:w-auto border-slate-700 hover:bg-slate-800 text-slate-300 text-xs"
            onClick={() => onOpenChange(false)}
          >
            Fechar
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
