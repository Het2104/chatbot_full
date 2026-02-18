"use client";

import { useState, useRef } from "react";
import { uploadPdf } from "../services/api";

interface PdfUploadButtonProps {
	onUploadSuccess?: (filename: string, numChunks: number) => void;
	onUploadError?: (error: string) => void;
}

export default function PdfUploadButton({ 
	onUploadSuccess, 
	onUploadError 
}: PdfUploadButtonProps) {
	const [isUploading, setIsUploading] = useState(false);
	const fileInputRef = useRef<HTMLInputElement>(null);

	const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
		const file = event.target.files?.[0];
		if (!file) return;

		// Validate file type
		if (!file.name.toLowerCase().endsWith(".pdf")) {
			const error = "Please select a PDF file";
			onUploadError?.(error);
			alert(error);
			return;
		}

		// Validate file size (10MB)
		const maxSize = 10 * 1024 * 1024; // 10MB
		if (file.size > maxSize) {
			const error = "File too large. Maximum size is 10MB";
			onUploadError?.(error);
			alert(error);
			return;
		}

		setIsUploading(true);

		try {
			const result = await uploadPdf(file);
			
			if (result.success) {
				const numChunks = result.stats?.num_chunks || 0;
				const message = `✅ ${result.message}`;
				
				onUploadSuccess?.(result.filename, numChunks);
				alert(message);
			} else {
				const error = result.error || "Upload failed";
				onUploadError?.(error);
				alert(`❌ ${error}`);
			}
		} catch (error) {
			const errorMessage = error instanceof Error ? error.message : "Upload failed";
			onUploadError?.(errorMessage);
			alert(`❌ ${errorMessage}`);
		} finally {
			setIsUploading(false);
			// Reset file input
			if (fileInputRef.current) {
				fileInputRef.current.value = "";
			}
		}
	};

	const handleClick = () => {
		fileInputRef.current?.click();
	};

	return (
		<>
			<input
				ref={fileInputRef}
				type="file"
				accept=".pdf"
				onChange={handleFileSelect}
				style={{ display: "none" }}
			/>
			<button
				onClick={handleClick}
				disabled={isUploading}
				style={{
					padding: "10px 15px",
					backgroundColor: isUploading ? "#cccccc" : "#4CAF50",
					color: "white",
					border: "none",
					borderRadius: "5px",
					cursor: isUploading ? "not-allowed" : "pointer",
					fontSize: "16px",
					display: "flex",
					alignItems: "center",
					gap: "8px",
					transition: "background-color 0.2s",
				}}
				onMouseEnter={(e) => {
					if (!isUploading) {
						e.currentTarget.style.backgroundColor = "#45a049";
					}
				}}
				onMouseLeave={(e) => {
					if (!isUploading) {
						e.currentTarget.style.backgroundColor = "#4CAF50";
					}
				}}
				title="Upload PDF to index"
			>
				{isUploading ? (
					<>
						<span style={{ 
							display: "inline-block",
							width: "16px",
							height: "16px",
							border: "2px solid white",
							borderTopColor: "transparent",
							borderRadius: "50%",
							animation: "spin 1s linear infinite"
						}} />
						<span>Processing...</span>
						<style jsx>{`
							@keyframes spin {
								to { transform: rotate(360deg); }
							}
						`}</style>
					</>
				) : (
					<>
						<span style={{ fontSize: "20px" }}>📎</span>
						<span>Upload PDF</span>
					</>
				)}
			</button>
		</>
	);
}
