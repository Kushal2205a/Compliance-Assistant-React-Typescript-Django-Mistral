import React, { useState } from 'react';

const FileUploader: React.FC = () => {
    const [file, setFile] = useState<File | null>(null);
    const handleUpload = async () => {
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file, file.name);

        try {
            const res = await fetch(`${import.meta.env.VITE_API_URL}/upload/`, {
                method: "POST",
                body: formData,
            });
            const data = await res.json();
            console.log("Uploaded", data);

        } catch (err) {
            console.error("Upload failed", err);

        }

    };

    return (
        <div className="flex items-center space-x-4">
            <input
                type="file"
                accept=".pdf"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="text-sm text-gray-600"
            />
            <button
                onClick={handleUpload}
                className="text-sm px-4 py-1 bg-gray-900 text-white rounded"
            >
                Upload
            </button>
        </div>


    );


};

export default FileUploader;