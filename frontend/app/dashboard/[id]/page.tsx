import DashboardLayout from '@/components/Dashboard/Layout';

interface PageProps {
    params: Promise<{ id: string }>;
}

export default async function DashboardPage({ params }: PageProps) {
    const resolvedParams = await params;
    return <DashboardLayout chatbotId={resolvedParams.id} />;
}
