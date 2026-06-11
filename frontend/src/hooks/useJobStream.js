import { useEffect, useState } from 'react';

import { jobStreamUrl } from '../api/client.js';

// Number of most-recently-completed results kept for the live feed
// (ISSUE 3.4 AC: "most recent 10 completed labels").
const MAX_RECENT_RESULTS = 10;

// Streams batch progress for `jobId` over Server-Sent Events (ISSUE 3.2,
// FedRAMP SC-8). The browser's EventSource reconnects automatically if the
// connection drops, and the backend replays any results the client missed
// on the next connection.
export default function useJobStream(jobId) {
  const [completed, setCompleted] = useState(0);
  const [total, setTotal] = useState(0);
  const [recentResults, setRecentResults] = useState([]);
  const [summary, setSummary] = useState(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!jobId) return undefined;

    setCompleted(0);
    setTotal(0);
    setRecentResults([]);
    setSummary(null);
    setDone(false);

    const source = new EventSource(jobStreamUrl(jobId));

    const handleProgress = (event) => {
      const data = JSON.parse(event.data);
      setCompleted(data.completed);
      setTotal(data.total);
      setRecentResults((prev) => [data.latest, ...prev].slice(0, MAX_RECENT_RESULTS));
    };

    // The backend emits a named `error` SSE event for a failed *label*
    // (data.latest.overall_status === 'ERROR'), carrying the same shape as
    // `progress`. EventSource also dispatches a connection-level "error"
    // event with no `data` when the stream itself drops — both arrive
    // through this listener, so tell them apart by the presence of `data`.
    const handleError = (event) => {
      if (event.data) {
        handleProgress(event);
      }
    };

    const handleComplete = (event) => {
      const data = JSON.parse(event.data);
      setCompleted(data.completed);
      setTotal(data.total);
      setSummary(data.summary);
      setDone(true);
      source.close();
    };

    source.addEventListener('progress', handleProgress);
    source.addEventListener('error', handleError);
    source.addEventListener('complete', handleComplete);

    return () => source.close();
  }, [jobId]);

  return { completed, total, recentResults, summary, done };
}
