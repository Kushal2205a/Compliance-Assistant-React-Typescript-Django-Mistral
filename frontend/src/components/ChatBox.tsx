import React, { use, useState } from 'react';
import "tailwindcss";

interface ChatMessage {
    role: 'user' | 'assistant'
    content: string

}

const ChatBox: React.FC = () => {
    const [input, setInput] = useState('');
    const [messages, setMessage] = useState<ChatMessage[]>([]);

    const sendMessage = async () => {
        if (!input.trim()) return;

        const UserMessage: ChatMessage = { role: "user", content: input };
        setMessage([...messages, UserMessage]);
        setInput("");

        try {
            const res = await fetch('${import.meta.env.VITE_API_URL} /ask/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: input }),
            });

            const data = await res.json()
            const assistantMessage: ChatMessage = { role: 'assistant', content: data.answer }
            setMessage((prev) => [...messages, assistantMessage]);

        } catch (err) {
            console.error('Failed to Fetch answer', err)
        }

    };
    return (
        <div className="space-y-4">
            <div className="space-y-3 text-sm leading-relaxed">
                {messages.map((msg, i) => (
                    <div key={i} className="whitespace-pre-wrap">
                        {msg.content}
                    </div>
                ))}
            </div>

            <div className="flex border rounded-lg px-3 py-2">
                <input
                    className="flex-1 text-sm outline-none"
                    placeholder="Ask something..."
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                />
                <button
                    onClick={sendMessage}
                    className="ml-3 text-sm text-white bg-black px-4 py-1 rounded"
                >
                    Ask
                </button>
            </div>
        </div>

    );
};

export default ChatBox; 