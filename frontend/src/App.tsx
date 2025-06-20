import React from 'react'
import FileUploader from './components/FileUploader'
import ChatBox from './components/ChatBox'
import "tailwindcss";

function App() {

  return (
    <div className="min-h-screen bg-white text-gray-900 px-4 py-10 font-sans">
      <div className="max-w-2xl mx-auto space-y-8">
        <ChatBox />
      </div>
    </div>



  )
}

export default App
