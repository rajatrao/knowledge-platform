import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

export function Dashboard({ persona, onAsk }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [open, setOpen] = useState(null);

  useEffect(() => {
    api(`/v1/dashboards/${persona}`).then(setData).catch((err) => setError(err.message));
  }, [persona]);

  if (error) return <p className="form-error">{error}</p>;
  if (!data) return <p className="muted">Loading figures…</p>;

  return (
    <section className="dashboard">
      {data.files ? <FileBoard files={data.files} /> : <PersonaBoard data={data} open={open} setOpen={setOpen} />}
      {persona === "ceo" ? <CeoThemes data={data} /> : null}
      {persona === "marketing" ? <ValueLanguage data={data} open={open} setOpen={setOpen} /> : null}
      <button type="button" className="starter" onClick={() => onAsk(data.sample_question)}>
        {data.sample_question}
      </button>
    </section>
  );
}

function FileBoard({ files }) {
  if (files.persona === "ceo") return <CeoFiles files={files} />;
  if (files.persona === "operations_manager") return <OperationsFiles files={files} />;
  if (files.persona === "engineer") return <EngineerFiles files={files} />;
  if (files.persona === "marketing") return <MarketingFiles files={files} />;
  return null;
}

function CeoFiles({ files }) {
  return (
    <div className="fact-block">
      <h2>Company snapshot</h2>
      <p className="source-note">{files.source_note}</p>
      <MetricGrid metrics={files.metrics} />
      {files.week_over_week ? <WeekOverWeek block={files.week_over_week} /> : null}
      <h2>Markets to review</h2>
      <div className="metric-grid market-grid">
        {files.markets.map((market) => (
          <article key={market.market_id} className="metric">
            <span className="eyebrow">{market.role}</span>
            <strong>{market.name}</strong>
            <small>{market.market_id}</small>
            {market.lines.map((line) => (
              <p key={line}>{line}</p>
            ))}
          </article>
        ))}
      </div>
      <h2>Open executive risks</h2>
      <p className="source-note">{files.open_risk_count} open in executive_risks.csv</p>
      <ol className="ranked">
        {files.risks.map((risk) => (
          <li key={risk.risk_id}>
            {risk.risk_id} {risk.severity} · {risk.title}
            {risk.observed_value ? <strong> {risk.observed_value}</strong> : null}
          </li>
        ))}
      </ol>
      <h2>Open executive alerts</h2>
      <p className="source-note">{files.open_alert_count} open in executive_alerts.csv</p>
      <ol className="ranked">
        {files.alerts.map((alert) => (
          <li key={alert.alert_id}>
            {alert.alert_id} {alert.severity} · {alert.title}
          </li>
        ))}
      </ol>
    </div>
  );
}

function WeekOverWeek({ block }) {
  return (
    <div className="fact-block">
      <h2>Week over week</h2>
      <p className="source-note">
        Week of {block.previous_week} to week of {block.latest_week}. {block.source}
      </p>
      <ol className="ranked">
        {block.rows.map((row) => (
          <li key={row.key}>
            {row.label} <strong>{row.latest}</strong>
            <span> was {row.previous}</span>
          </li>
        ))}
      </ol>
      {block.note ? <p className="source-note">{block.note}</p> : null}
    </div>
  );
}

function OperationsFiles({ files }) {
  return (
    <div className="fact-block">
      <h2>Operations</h2>
      <p className="source-note">{files.source_note}</p>
      <MetricGrid metrics={files.metrics} />
      <h2>Open operational alerts</h2>
      <ol className="ranked">
        {files.alerts.map((alert) => (
          <li key={alert.alert_id}>
            <strong>{alert.alert_id}</strong> {alert.severity} · {alert.alert_type} · {alert.entity_id}
            <p>{alert.description}</p>
          </li>
        ))}
      </ol>
      <h2>Jobs waiting for parts</h2>
      <ol className="ranked">
        {files.waiting_jobs.map((job) => (
          <li key={job.job_id}>
            {job.job_id} {job.job_type} · {job.city || "city not on the site row"} · {job.technician_id || "unassigned"} · {job.van_id || "no van"}
          </li>
        ))}
      </ol>
      <h2>Van kit gap</h2>
      {files.kit_gaps.length ? (
        <ol className="ranked">
          {files.kit_gaps.map((gap) => (
            <li key={`${gap.job_id}-${gap.part_id}`}>
              {gap.van_id || "No van"} with {gap.technician_id || "no technician"} on {gap.job_id}
              {gap.city ? ` in ${gap.city}` : ""} is short {gap.part_id} {gap.part_name}. Required {gap.required_quantity}, van quantity {gap.van_quantity}. {gap.inventory_note}.
            </li>
          ))}
        </ol>
      ) : (
        <p className="source-note">No missing van part on a job waiting for parts.</p>
      )}
      <h2>Warehouse supply</h2>
      <ol className="ranked">
        {files.supply_hints.map((hint) => (
          <li key={`${hint.job_id}-${hint.part_id}`}>
            {hint.job_id} is {hint.job_status} on {hint.part_id} {hint.part_name}.{" "}
            {hint.warehouses.map((row) => `${row.warehouse_id} available ${row.quantity_available}`).join(". ")}.
          </li>
        ))}
      </ol>
    </div>
  );
}

function EngineerFiles({ files }) {
  return (
    <div className="fact-block">
      <h2>Engineering</h2>
      <p className="source-note">{files.source_note}</p>
      <MetricGrid metrics={files.metrics} />
      <h2>Offline and faulted</h2>
      <ol className="ranked">
        {[...files.offline, ...files.faulted].map((device) => (
          <li key={device.device_id}>
            {device.device_id} {device.device_type} · {device.status} · firmware {device.firmware_version} · {device.site_id}
          </li>
        ))}
      </ol>
      <h2>Active incidents</h2>
      <ol className="ranked">
        {files.active_incidents.map((incident) => (
          <li key={incident.incident_id}>
            {incident.incident_id} {incident.status} · {incident.title}
          </li>
        ))}
      </ol>
      <h2>Under investigation</h2>
      <ol className="ranked">
        {files.under_investigation.map((incident) => (
          <li key={incident.incident_id}>
            {incident.incident_id} status {incident.status}. confirmed_root_cause is {incident.confirmed_root_cause}. {incident.title}
          </li>
        ))}
      </ol>
      <h2>Proactive watch</h2>
      <p className="source-note">DEV-054, DEV-061, and DEV-062 from devices.csv.</p>
      <ol className="ranked">
        {files.proactive_watch.map((device) => (
          <li key={device.device_id}>
            {device.device_id} {device.device_type} · status {device.status} · firmware {device.firmware_version} · {device.site_id}
          </li>
        ))}
      </ol>
      {files.proactive_incident ? (
        <p className="source-note">
          {files.proactive_incident.incident_id} status {files.proactive_incident.status}. {files.proactive_incident.title}
        </p>
      ) : null}
    </div>
  );
}

function MarketingFiles({ files }) {
  const north = files.north_austin;
  return (
    <div className="fact-block">
      <h2>Customer satisfaction</h2>
      <p className="source-note">{files.source_note}</p>
      {north ? (
        <article className="metric">
          <span className="eyebrow">North Austin</span>
          <strong>{north.to_csat || "—"}</strong>
          <small>
            {north.name} csat_score moved from {north.from_csat} in the week of {north.from_week} to {north.to_csat} in the week of {north.to_week}.
          </small>
          <p>
            Latest week response time {north.to_response_hours} hours, repeat contact rate {north.to_repeat_contact_rate}, installation complaints {north.to_installation_complaints}. NPS {north.to_nps}. {north.source}.
          </p>
          {north.comparison_csat ? (
            <p>
              {north.comparison_name} ({north.comparison_market_id}) csat_score in the week of {north.comparison_week} is {north.comparison_csat}.
            </p>
          ) : null}
        </article>
      ) : null}
      <div className="metric-grid">
        {files.satisfaction.map((row) => (
          <article key={row.market_id} className="metric">
            <span>{row.name}</span>
            <strong>{row.csat_score}</strong>
            <small>
              {row.market_id} · week of {row.week_start} · {row.installation_complaint_count} installation complaints
            </small>
          </article>
        ))}
      </div>
      <h2>Customer issue categories</h2>
      <p className="source-note">customer_issues.csv</p>
      <ol className="ranked">
        {files.categories.map((row) => (
          <li key={row.category}>
            {row.category} <strong>{row.count}</strong>
            <span>
              {" "}
              {row.open} open
              {row.north_austin_open ? `, ${row.north_austin_open} open in North Austin` : ""}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}

function MetricGrid({ metrics }) {
  return (
    <div className="metric-grid">
      {metrics.map((metric) => (
        <article key={metric.key} className="metric">
          <span>{metric.label}</span>
          <strong>{metric.value}</strong>
          <small>{metric.detail}</small>
          <small>{metric.source}</small>
        </article>
      ))}
    </div>
  );
}

function CeoThemes({ data }) {
  if (!data.themes?.length) return null;
  return (
    <div>
      <h2>Complaint themes</h2>
      <div className="metric-grid">
        {data.themes.map((theme) => (
          <Link key={theme.slug} className="metric" to={`/investigations/${theme.slug}`}>
            <span>{theme.name}</span>
            <strong>{theme.complaint_count}</strong>
            <small>{theme.trend}% vs previous period</small>
          </Link>
        ))}
      </div>
    </div>
  );
}

function ValueLanguage({ data, open, setOpen }) {
  return (
    <div>
      <h2>Value language</h2>
      <div className="metric-grid">
        {data.sentiment.map((row) => (
          <button type="button" key={row.key} className="metric" onClick={() => setOpen(open === row.key ? null : row.key)}>
            <span>{row.label}</span>
            <strong>{Math.round(row.share * 1000) / 10}%</strong>
            <small>{row.count} conversations</small>
          </button>
        ))}
      </div>
      <ol className="ranked">
        {data.value_themes.map((theme) => (
          <li key={theme.key}>
            <button type="button" onClick={() => setOpen(open === theme.key ? null : theme.key)}>
              {theme.label} <strong>{theme.count}</strong>
            </button>
          </li>
        ))}
      </ol>
      <Evidence open={open} groups={[...data.sentiment, ...data.value_themes]} />
    </div>
  );
}

function PersonaBoard({ data, open, setOpen }) {
  if (data.persona === "operations_manager") {
    return (
      <div>
        <h2>Operations</h2>
        <div className="metric-grid">
          {data.metrics.map((metric) => (
            <button type="button" key={metric.key} className="metric" onClick={() => setOpen(open === metric.key ? null : metric.key)}>
              <span>{metric.label}</span>
              <strong>{metric.value}</strong>
            </button>
          ))}
        </div>
        <ol className="ranked">
          {data.blockers.map((blocker) => (
            <li key={blocker.key}>
              <button type="button" onClick={() => setOpen(open === blocker.key ? null : blocker.key)}>
                {blocker.label} <strong>{blocker.count}</strong>
              </button>
            </li>
          ))}
        </ol>
        <Evidence open={open} groups={[...data.metrics, ...data.blockers.map((row) => ({ ...row, value: row.count }))]} />
      </div>
    );
  }
  if (data.persona === "engineer") {
    return (
      <div>
        <h2>Engineering</h2>
        <div className="metric-grid">
          {data.technical_issues.map((issue) => (
            <button type="button" key={issue.key} className="metric" onClick={() => setOpen(open === issue.key ? null : issue.key)}>
              <span>{issue.label}</span>
              <strong>{issue.complaint_count}</strong>
            </button>
          ))}
        </div>
        <ol className="ranked">
          {data.related_incidents.map((incident) => (
            <li key={incident.id}>
              <button type="button" onClick={() => setOpen(open === incident.id ? null : incident.id)}>
                {incident.id} <strong>{incident.linked_conversations}</strong>
              </button>
            </li>
          ))}
        </ol>
        <Evidence
          open={open}
          groups={[
            ...data.technical_issues.map((row) => ({ key: row.key, records: row.records })),
            ...data.related_incidents.map((row) => ({ key: row.id, records: row.records })),
          ]}
        />
      </div>
    );
  }
  return null;
}

function Evidence({ open, groups }) {
  const group = groups.find((item) => item.key === open);
  if (!group) return null;
  return (
    <div className="evidence">
      <h3>Evidence</h3>
      <ul>
        {(group.records || []).slice(0, 12).map((record) => (
          <li key={`${record.id}-${record.complaint_id || ""}`}>
            <strong>{record.id}</strong>
            <span>{record.date} · {record.region || "—"}</span>
            <p>{record.quote || record.text}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
