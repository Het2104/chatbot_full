"use client";

import { useState } from "react";
import { ingestUrl } from "../services/api";

interface UrlIngestButtonProps {
	onIngestSuccess?: (url: string, numChunks: number) => void;
	onIngestError?: (error: string) => void;
}

export default function UrlIngestButton({
	onIngestSuccess,
	onIngestError,
}: UrlIngestButtonProps) {
	const [isProcessing, setIsProcessing] = useState(false);
	const [urlInput, setUrlInput] = useState("");
	const [showInput, setShowInput] = useState(false);

	const handleSubmit = async () => {
		const url = urlInput.trim();

		if (!url) return;

		// Basic client-side validation — must be http or https
		if (!url.startsWith("http://") && !url.startsWith("https://")) {
			const error = "URL must start with http:// or https://";
			onIngestError?.(error);
			alert(error);
			return;
		}

		setIsProcessing(true);

		try {
			const result = await ingestUrl(url) as {
				success: boolean;
				message: string;
				url: string;
				title?: string;
				stats?: { num_chunks?: number };
				error?: string;
			};

			if (result.success) {
				const numChunks = result.stats?.num_chunks ?? 0;
				onIngestSuccess?.(result.url, numChunks);
				alert(`✅ ${result.message}${result.title ? `\nPage: ${result.title}` : ""}`);
				setUrlInput("");
				setShowInput(false);
			} else {
				const error = result.error || "Failed to ingest URL";
				onIngestError?.(error);
				alert(`❌ ${error}`);
			}
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : "Failed to ingest URL";
			onIngestError?.(errorMessage);
			alert(`❌ ${errorMessage}`);
		} finally {
			setIsProcessing(false);
		}
	};

	const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
		if (e.key === "Enter") handleSubmit();
		if (e.key === "Escape") {
			setShowInput(false);
			setUrlInput("");
		}
	};

	if (!showInput) {
		return (
			<button
				onClick={() => setShowInput(true)}
				style={{
					padding: "10px 15px",
					backgroundColor: "#2196F3",
					color: "white",
					border: "none",
					borderRadius: "5px",
					cursor: "pointer",
					fontSize: "16px",
					display: "flex",
					alignItems: "center",
					gap: "8px",
					transition: "background-color 0.2s",
				}}
				onMouseEnter={(e) => {
					e.currentTarget.style.backgroundColor = "#1976D2";
				}}
				onMouseLeave={(e) => {
					e.currentTarget.style.backgroundColor = "#2196F3";
				}}
				title="Index a website URL for RAG"
			>
				<span style={{ fontSize: "20px" }}>🔗</span>
				<span>Add URL</span>
			</button>
		);
	}

	return (
		<div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
			<input
				type="url"
				value={urlInput}
				onChange={(e) => setUrlInput(e.target.value)}
				onKeyDown={handleKeyDown}
				placeholder="https://example.com/page"
				disabled={isProcessing}
				autoFocus
				style={{
					padding: "9px 12px",
					border: "1px solid #2196F3",
					borderRadius: "5px",
					fontSize: "14px",
					width: "280px",
					outline: "none",
				}}
			/>
			<button
				onClick={handleSubmit}
				disabled={isProcessing || !urlInput.trim()}
				style={{
					padding: "10px 15px",
					backgroundColor: isProcessing || !urlInput.trim() ? "#cccccc" : "#2196F3",
					color: "white",
					border: "none",
					borderRadius: "5px",
					cursor: isProcessing || !urlInput.trim() ? "not-allowed" : "pointer",
					fontSize: "14px",
					display: "flex",
					alignItems: "center",
					gap: "6px",
					transition: "background-color 0.2s",
				}}
				onMouseEnter={(e) => {
					if (!isProcessing && urlInput.trim()) {
						e.currentTarget.style.backgroundColor = "#1976D2";
					}
				}}
				onMouseLeave={(e) => {
					if (!isProcessing && urlInput.trim()) {
						e.currentTarget.style.backgroundColor = "#2196F3";
					}
				}}
			>
				{isProcessing ? (
					<>
						<span
							style={{
								display: "inline-block",
								width: "14px",
								height: "14px",
								border: "2px solid white",
								borderTopColor: "transparent",
								borderRadius: "50%",
								animation: "spin 1s linear infinite",
							}}
						/>
						<span>Indexing...</span>
						<style jsx>{`
							@keyframes spin {
								to {
									transform: rotate(360deg);
								}
							}
						`}</style>
					</>
				) : (
					<span>Index</span>
				)}
			</button>
			<button
				onClick={() => {
					setShowInput(false);
					setUrlInput("");
				}}
				disabled={isProcessing}
				style={{
					padding: "10px 12px",
					backgroundColor: "transparent",
					color: "#666",
					border: "1px solid #ccc",
					borderRadius: "5px",
					cursor: isProcessing ? "not-allowed" : "pointer",
					fontSize: "14px",
				}}
				title="Cancel"
			>
				✕
			</button>
		</div>
	);
}
