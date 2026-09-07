import { getAllProspects } from "@/lib/data";
import OutcomeBoard from "./OutcomeBoard";

const CURRENT_CLASS = 2026;

export default function OutcomesPage() {
  const historical = getAllProspects().filter(
    (p) => p.draft_class !== CURRENT_CLASS && p.drafted !== null
  );

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <header className="border-b border-gray-800 px-6 py-4">
        <h1 className="text-2xl font-bold tracking-tight">
          Historical Outcomes{" "}
          <span className="text-gray-500 font-normal text-lg">2013 – 2025</span>
        </h1>
        <p className="text-gray-500 text-sm mt-1">
          {historical.length} drafted players · curate outcomes by position group
        </p>
      </header>
      <OutcomeBoard initialProspects={historical} />
    </div>
  );
}
