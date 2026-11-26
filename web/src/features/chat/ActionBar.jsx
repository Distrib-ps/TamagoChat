import { ACTION_GROUPS } from "../../constants.js";

export const ActionBar = ({ send }) => (
  <div class="actions">
    {ACTION_GROUPS.map(([title, list]) => (
      <div class="grp" key={title}>
        <span class="lbl">{title}</span>
        {list.map(([key, label]) => (
          <button class="chip" key={key} onClick={() => send({ kind: "action", action: key })}>{label}</button>
        ))}
      </div>
    ))}
  </div>
);
