import ChatInterface from "@/components/ChatInterface";

export default function Home() {
  return (
    <main className="h-screen flex flex-col max-w-3xl mx-auto px-4">
      <div className="pt-4 pb-2">
        <h1 className="text-3xl font-medium tracking-tight">
          Compliance QnA Assistant
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Upload a SOC2 compliance document and ask questions about it.
        </p>
      </div>
      <ChatInterface />
    </main>
  );
}
