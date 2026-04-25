import dynamic from "next/dynamic";
import { fetchOrNull, type EventRow, type Station } from "@/lib/api";

export const revalidate = 0;

const MapDeck = dynamic(() => import("@/components/MapDeck"), {
  ssr: false,
  loading: () => (
    <div className="h-[calc(100vh-4rem)] grid place-items-center text-[var(--fg-muted)]">
      Loading map…
    </div>
  ),
});

async function loadData() {
  const [events, stations] = await Promise.all([
    fetchOrNull<EventRow[]>("/events?min_prob=0.5"),
    fetchOrNull<Station[]>("/stations"),
  ]);
  return { events: events ?? [], stations: stations ?? [] };
}

export default async function MapPage() {
  const { events, stations } = await loadData();
  return (
    <section className="h-[calc(100vh-4rem)]">
      <MapDeck events={events} stations={stations} />
    </section>
  );
}
