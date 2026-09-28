import React from 'react';
import { QRCodeCanvas } from 'qrcode.react';

export interface TdevBrandedQrProps {
    value: string;
    /** Taille du canvas QR en pixels. */
    size?: number;
    className?: string;
    title?: string;
}

/** QR scannable (qrcode.react, niveau H, sans logo au centre). */
export function TdevBrandedQr({ value, size = 260, className = '', title = 'QR code billet Tdev' }: TdevBrandedQrProps) {
    const frame = size + 32;

    return (
        <div className={`flex justify-center ${className}`}>
            <div
                className="rounded-2xl border border-neutral-200 bg-white p-4"
                style={{ width: frame, height: frame }}
                role="img"
                aria-label={title}
            >
                <QRCodeCanvas
                    value={value}
                    size={size}
                    level="H"
                    marginSize={4}
                    fgColor="#0a0a0a"
                    bgColor="#ffffff"
                    title={title}
                    style={{ display: 'block', width: size, height: size }}
                />
            </div>
        </div>
    );
}
