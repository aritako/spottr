import type { Metadata } from "next";

import { RoutineDetail, getRoutine } from "~/features/routines";

interface RoutinePageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({
  params,
}: RoutinePageProps): Promise<Metadata> {
  const { slug } = await params;
  const routine = getRoutine(slug);
  return { title: routine ? routine.name : "Routine" };
}

export default async function RoutinePage({ params }: RoutinePageProps) {
  const { slug } = await params;

  return <RoutineDetail slug={slug} />;
}
