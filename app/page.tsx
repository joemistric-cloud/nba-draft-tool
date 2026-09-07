import { getProspectsByClass } from "@/lib/data";
import BigBoard from "./BigBoard";

const CURRENT_CLASS = 2026;

export default function Home() {
  const prospects = getProspectsByClass(CURRENT_CLASS);

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <header className="border-b border-gray-800 px-6 py-4">
        <h1 className="text-2xl font-bold tracking-tight">
          NBA Draft Big Board{" "}
          <span className="text-gray-400 font-normal">{CURRENT_CLASS}</span>
        </h1>
      </header>

      <main className="px-6 py-6">
        <BigBoard initialProspects={prospects} />
      </main>
    </div>
  );
}
