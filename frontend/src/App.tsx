import { QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "@tanstack/react-router";
import { PreferencesProvider } from "@/app/preferences";
import { queryClient } from "@/app/query-client";
import { router } from "@/router";

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <PreferencesProvider>
        <RouterProvider router={router} />
      </PreferencesProvider>
    </QueryClientProvider>
  );
}
