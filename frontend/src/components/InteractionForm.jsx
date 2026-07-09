import React from "react";
import { useSelector } from "react-redux";

function Value({ children, placeholder = "—" }) {
  const isEmpty =
    children === undefined ||
    children === null ||
    children === "" ||
    (Array.isArray(children) && children.length === 0);
  if (isEmpty) {
    return <div className="value placeholder">{placeholder}</div>;
  }
  return <div className="value">{children}</div>;
}

function ChipList({ items }) {
  if (!items || items.length === 0) {
    return <div className="value placeholder">No items added</div>;
  }
  return (
    <div className="chip-list">
      {items.map((item) => (
        <span className="chip" key={item}>
          {item}
        </span>
      ))}
    </div>
  );
}

export default function InteractionForm() {
  const form = useSelector((state) => state.interaction);

  return (
    <div className="form-panel">
      <div className="form-panel__title">Interaction Details</div>
      <div className="form-panel__lock-note">
        This form is read-only. All fields are populated and edited exclusively by the AI
        Assistant — describe or instruct changes in the chat panel on the right.
      </div>

      <div className="field-row">
        <div className="field">
          <label>HCP Name</label>
          <Value placeholder="Search or select HCP…">{form.hcp_name}</Value>
        </div>
        <div className="field">
          <label>Interaction Type</label>
          <Value>{form.interaction_type}</Value>
        </div>
      </div>

      <div className="field-row">
        <div className="field">
          <label>Date</label>
          <Value>{form.date}</Value>
        </div>
        <div className="field">
          <label>Time</label>
          <Value>{form.time}</Value>
        </div>
      </div>

      <div className="field field--full">
        <label>Attendees</label>
        <Value placeholder="Enter names or search…">{form.attendees}</Value>
      </div>

      <div className="field field--full" style={{ marginBottom: 14 }}>
        <label>Topics Discussed</label>
        <Value placeholder="Enter key discussion points…">{form.topics_discussed}</Value>
      </div>

      <div className="field-row">
        <div className="field">
          <label>Materials Shared</label>
          <ChipList items={form.materials_shared} />
        </div>
        <div className="field">
          <label>Samples Distributed</label>
          <ChipList items={form.samples_distributed} />
        </div>
      </div>

      <div className="field field--full" style={{ marginBottom: 14 }}>
        <label>Observed / Inferred HCP Sentiment</label>
        <div className="sentiment-row">
          {["Positive", "Neutral", "Negative"].map((s) => (
            <span
              key={s}
              className={`sentiment-pill ${form.sentiment === s ? `active--${s}` : ""}`}
            >
              {s}
            </span>
          ))}
        </div>
      </div>

      <div className="field field--full" style={{ marginBottom: 14 }}>
        <label>Outcomes</label>
        <Value placeholder="Key outcomes or agreements…">{form.outcomes}</Value>
      </div>

      <div className="field field--full" style={{ marginBottom: 14 }}>
        <label>Follow-up Actions</label>
        <Value placeholder="Enter next steps or tasks…">{form.follow_up_actions}</Value>
      </div>

      {form.ai_suggested_followups && form.ai_suggested_followups.length > 0 && (
        <div className="field field--full">
          <label>AI Suggested Follow-ups</label>
          <ul className="suggested-followups">
            {form.ai_suggested_followups.map((item) => (
              <li key={item}>+ {item}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
