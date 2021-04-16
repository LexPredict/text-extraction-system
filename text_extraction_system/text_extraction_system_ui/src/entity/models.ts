export class UploadRequest {
    id: string;
    fileName: string;
    started: Date;
}


export class UploadTask extends UploadRequest {
    status: string;
}

export class UploadTaskSettings {
    language: string;
    ocr_enable: boolean;
    output_format: string;
    convert_to_pdf_timeout_sec: number;
    pdf_to_images_timeout_sec: number;

    constructor() {
        this.convert_to_pdf_timeout_sec = 60 * 15;
        this.pdf_to_images_timeout_sec = 60 * 15;
        this.remove_non_printable = true;
        this.ocr_enable = true;
        this.output_format = 'json';
    }
}