import { Card } from '@/components/ui/card';

export function PlaceholderView({ title }: { title: string }) {
  return (
    <div className="h-full flex items-center justify-center">
      <Card className="p-12 text-center max-w-md">
        <div className="text-6xl mb-4">🚧</div>
        <h2 className="text-2xl font-semibold mb-2">{title}</h2>
        <p className="text-muted-foreground">
          Este módulo está em desenvolvimento e será implementado em breve.
        </p>
      </Card>
    </div>
  );
}
