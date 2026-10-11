import { RouterProvider } from "@tanstack/react-router";
import { PreferencesProvider } from "@/app/preferences";
import { router } from "@/router";

export default function App() {
  return (
    <PreferencesProvider>
      <RouterProvider router={router} />
    </PreferencesProvider>
  );
}
