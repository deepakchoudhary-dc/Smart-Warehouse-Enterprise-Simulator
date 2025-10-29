interface RunPlaybackControlsProps {
  mode: "live" | "replay";
  historyLength: number;
  cursor: number;
  onModeChange: (mode: "live" | "replay") => void;
  onSeek: (index: number) => void;
}

export function RunPlaybackControls({ mode, historyLength, cursor, onModeChange, onSeek }: RunPlaybackControlsProps) {
  const disableReplay = historyLength <= 1;
  const maxIndex = Math.max(historyLength - 1, 0);
  return (
    <div className="playback-controls">
      <div className="playback-modes">
        <button type="button" className={mode === "live" ? "active" : "ghost"} onClick={() => onModeChange("live")}>Live</button>
        <button
          type="button"
          className={mode === "replay" ? "active" : "ghost"}
          onClick={() => onModeChange("replay")}
          disabled={disableReplay}
        >
          Replay
        </button>
      </div>
      <div className="playback-slider">
        <input
          type="range"
          min={0}
          max={maxIndex}
          value={Math.min(cursor, maxIndex)}
          disabled={mode !== "replay" || disableReplay}
          onChange={(event) => onSeek(Number(event.target.value))}
        />
        <span className="playback-index">{historyLength ? `${cursor + 1}/${historyLength}` : "0/0"}</span>
      </div>
    </div>
  );
}
