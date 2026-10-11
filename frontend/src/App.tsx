import { PreferencesProvider } from "@/app/preferences";
import { ChatPage } from "@/features/chat/chat-page";

export default function App() {
  return (
    <PreferencesProvider>
      <ChatPage />
    </PreferencesProvider>
  );
}
