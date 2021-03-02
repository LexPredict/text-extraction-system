export class UploadRequest {
    id: string;
    fileName: string;
    started: Date;
}


export class UploadTask extends UploadRequest {
    status: string;
}