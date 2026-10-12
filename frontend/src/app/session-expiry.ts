// A staff session ends after 8 hours. When a staff API call then answers 401, go to the login
// page (and come back afterwards) instead of showing broken pages.
import { client } from "@/client/client.gen";
import { router } from "@/router";
import { queryClient } from "./query-client";

export function watchForExpiredSessions(): void {
  client.interceptors.response.use((response, request) => {
    if (response.status === 401 && new URL(request.url).pathname.startsWith("/api/staff")) {
      queryClient.clear(); // nothing from the old session stays in memory
      const back = router.state.location.href;
      void router.navigate({ to: "/staff/login", search: { redirect: back } });
    }
    return response;
  });
}
