import React, { useState } from 'react';
import "tailwindcss";

interface ChatMessage {
    role: 'user' | 'assistant'
    content: string
}

const ChatBox: React.FC = () => {
    const [input, setInput] = useState('');
    const [file, setFile] = useState<File | null>(null);
    const [messages, setMessage] = useState<ChatMessage[]>([]);
    const [progress, setProgress] = useState<string[]>([]);
    const [loading, setLoading] = useState(false);

    const sendMessage = async () => {
        if (!input.trim()) return;

        const UserMessage: ChatMessage = { role: "user", content: input };
        setMessage((prev) => [...prev, UserMessage]);
        setInput('');
        setProgress([]);
        setLoading(true);

        const formData = new FormData();
        formData.append('query', input);
        if (!file) {
            setLoading(false);
            return;
        }
        formData.append('pdf', file);

        try {
            const res = await fetch(import.meta.env.VITE_API_URL + '/query/', {
                method: 'POST',
                body: formData,
            });

            if (res.body) {
                const reader = res.body.getReader();
                let result = '';
                setLoading(true);

                // Add assistant message if not present
                setMessage((prev) => {
                    if (prev.length && prev[prev.length - 1].role === 'assistant') {
                        return prev;
                    } else {
                        return [...prev, { role: 'assistant', content: '' }];
                    }
                });

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    result += new TextDecoder().decode(value);
                    setMessage((prev) => {
                        // Update last assistant message as it streams
                        if (prev.length && prev[prev.length - 1].role === 'assistant') {
                            const updated = [...prev];
                            updated[updated.length - 1] = { role: 'assistant', content: result };
                            return updated;
                        } else {
                            return [...prev, { role: 'assistant', content: result }];
                        }
                    });
                }
                setLoading(false);
            } else {
                setMessage((prev) => [
                    ...prev,
                    { role: "assistant", content: "⚠️ No response body from server." },
                ]);
                setLoading(false);
            }
        } catch (err) {
            console.error('Failed to Fetch answer', err)
            setMessage((prev) => [...prev, { role: 'assistant', content: "Error Communiating with the server" }])
            setLoading(false);
        }
    };

    return (
        <div className="grid grid-rows-[auto_auto_1fr_auto] h-screen max-w-3xl mx-auto px-4 gap-3">
            {/* Header - Row 1 */}
            <div className="pt-4 font-mono" >
                <h1 className="text-3xl font-medium">Compliance QnA Assistant</h1>
            </div>

            {/* File Upload Container*/}
            <div className="relative w-full">
                <input
                    type="file"
                    accept=".pdf"
                    id="pdf-upload"
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                    className="hidden"
                />
                <input
                    type="text"
                    value={file?.name || ""}
                    placeholder="Upload a PDF..."
                    readOnly
                    className="w-full border rounded-full py-2 px-4 pr-12 text-sm focus:outline-none"
                />
                <label
                    htmlFor="pdf-upload"
                    className="absolute right-2 top-1/2 -translate-y-1/2 bg-yellow-500 text-white rounded-full w-8 h-8 flex items-center justify-center cursor-pointer hover:bg-gray-800"
                    title="Upload PDF"
                >
                    📎
                </label>
            </div>

            {/* Progress and Messages Container*/}
            <div className="overflow-y-auto rounded-lg min-h-0" style={{maxHeight: '100%'}}>
                <div className="p-3 space-y-4 pb-28">
                    {progress.length > 0 && (
                        <div className="text-sm text-gray-500">
                            <div className="mb-2 font-semibold">Processing steps:</div>
                            <ul className="list-disc ml-6">
                                {progress.map((step, idx) => (
                                    <li key={idx}>{step}</li>
                                ))}
                            </ul>
                        </div>
                    )}
                    {messages.map((msg, i) => (
                        <div
                            key={i}
                            className={`whitespace-pre-wrap ${msg.role === 'user' ? 'text-right' : 'text-left'}`}
                        >
                            <span
                                className={`inline-block p-2 rounded-lg max-w-[80%] ${msg.role === 'user'
                                    ? 'bg-yellow-500 text-white'
                                    : 'bg-gray-200 text-gray-800'
                                    }`}
                            >
                                <strong>{msg.role === 'user' ? 'You' : '🤖'}:</strong>{' '}
                                {msg.content}
                            </span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Input Container */}
            <div className="sticky bottom-0 bg-white py-3 z-10">
                <div className="flex border rounded-lg p-2 bg-white">
                    <input
                        className="flex-grow px-2 py-1 text-sm outline-none"
                        type="text"
                        placeholder="Ask something..."
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                                sendMessage();
                            }
                        }}
                    />
                    <button
                        onClick={sendMessage}
                        className="ml-2 bg-yellow-500 text-white px-4 py-1 rounded text-sm"
                    >
                        Ask
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ChatBox;