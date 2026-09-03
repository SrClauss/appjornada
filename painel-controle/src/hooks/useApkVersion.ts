import { useState, useEffect } from 'react';
import { api } from '@/lib/api';

export interface ApkVersionInfo {
  versao: string;
  versaoCompleta: string;
  urlDownload: string;
  nomeArquivo: string;
  tamanhoMb?: string;
  loading: boolean;
}

export function useApkVersion(): ApkVersionInfo {
  const [info, setInfo] = useState<ApkVersionInfo>({
    versao: '1.2.4',
    versaoCompleta: '1.2.4+17',
    urlDownload: `${api.defaults.baseURL || ''}/config/apk/download`,
    nomeArquivo: 'app-jornada-v1.2.4.apk',
    loading: true,
  });

  useEffect(() => {
    let isMounted = true;
    api
      .get('/config/versao-app')
      .then((res) => {
        if (isMounted && res.data) {
          const rawUrl = res.data.url_download || '/config/apk/download';
          const fullUrl = rawUrl.startsWith('http')
            ? rawUrl
            : `${api.defaults.baseURL || ''}${rawUrl.startsWith('/') ? '' : '/'}${rawUrl}`;

          const vMaisRecente = res.data.versao_mais_recente || '1.2.4';
          setInfo({
            versao: vMaisRecente,
            versaoCompleta: res.data.versao_completa || `${vMaisRecente}+17`,
            urlDownload: fullUrl,
            nomeArquivo: `app-jornada-v${vMaisRecente}.apk`,
            tamanhoMb: res.data.tamanho_mb,
            loading: false,
          });
        }
      })
      .catch((err) => {
        console.error('Erro ao carregar versão do APK do backend:', err);
        if (isMounted) {
          setInfo((prev) => ({ ...prev, loading: false }));
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return info;
}
