import { ActionBar } from "./ActionBar.jsx";
import { Composer } from "./Composer.jsx";
import { Feed } from "./Feed.jsx";

export const ChatPane = ({ selected, send, feedVersion }) => (
  <section class="flex min-h-0 flex-1 animate-fade flex-col">
    <ActionBar send={send} />
    <Feed selected={selected} version={feedVersion} />
    <Composer send={send} />
  </section>
);
