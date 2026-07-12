import AlertForm from "../components/AlertForm";

export default function Subscribe() {
  return (
    <div className="mx-auto max-w-xl px-4 py-8">
      <h1 className="font-display text-3xl font-bold text-center">Alertes email</h1>
      <p className="mt-2 mb-8 text-center text-ink/60 dark:text-cream/60">
        Recevez les nouveaux événements des musées franciliens qui correspondent à vos envies.
      </p>
      <AlertForm />
    </div>
  );
}
