import { ActionBar } from "./ActionBar.jsx";
import { Composer } from "./Composer.jsx";
import { Feed } from "./Feed.jsx";

export const ChatPane = ({ selected, send, feedVersion }) => (
  <section class="pane-chat">
    <ActionBar send={send} />
    <Feed selected={selected} version={feedVersion} />
    <Composer send={send} />
  </section>
);
