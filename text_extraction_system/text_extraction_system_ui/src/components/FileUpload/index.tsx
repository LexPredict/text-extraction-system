import React, { Component } from 'react';
import { FileUploaderPresentationalComponent } from '../UploadPresentationalComponent';
import styles from './FileUpload.module.css'; 

type State = {
    dragging: boolean;
    file: File | null;
}


type FileUploaderProps = {
    fileSelected: (file: File) => void;
};


export default class FileUploader extends Component<FileUploaderProps, State> {
    static counter = 0;
    fileUploaderInput: HTMLElement | null = null;
    dragEventCounter = 0;

    constructor(props) {
        super(props);
        this.state = { dragging: false, file: null };
    }

    resetFile(): void {
        this.setState({ dragging: false, file: null });
        this.props.fileSelected(null);
        // setTimeout(() => { console.log('State is:'); console.log(this.state);}, 1000);
    }
    
    dragenterListener = (event: React.DragEvent<HTMLDivElement>) => {
        this.overrideEventDefaults(event);
        this.dragEventCounter++;
        if (event.dataTransfer.items && event.dataTransfer.items[0]) {
            this.setState({ dragging: true });
        } else if (
            event.dataTransfer.types &&
            event.dataTransfer.types[0] === "Files"
        ) {
            // This block handles support for IE - if you're not worried about
            // that, you can omit this
            this.setState({ dragging: true });
        }
    };

    dragleaveListener = (event: React.DragEvent<HTMLDivElement>) => {
        this.overrideEventDefaults(event);
        this.dragEventCounter--;

        if (this.dragEventCounter === 0) {
            this.setState({ dragging: false });
        }
    };

    dropListener = (event: React.DragEvent<HTMLDivElement>) => {
        this.overrideEventDefaults(event);
        this.dragEventCounter = 0;
        this.setState({ dragging: false });

        if (event.dataTransfer.files && event.dataTransfer.files[0]) {
            this.setState({ file: event.dataTransfer.files[0] });
            this.props.fileSelected(event.dataTransfer.files[0]);
        }
    };

    overrideEventDefaults = (event: Event | React.DragEvent<HTMLDivElement>) => {
        event.preventDefault();
        event.stopPropagation();
    };

    onSelectFileClick = () => {
        this.fileUploaderInput && this.fileUploaderInput.click();
    };

    onFileChanged = (event: React.ChangeEvent<HTMLInputElement>) => {
        if (event.target.files && event.target.files[0]) {
            this.setState({ file: event.target.files[0] });
            this.props.fileSelected(event.target.files[0]);
        }
    };

    componentDidMount() {
        window.addEventListener("dragover", (event: Event) => {
            this.overrideEventDefaults(event);
        });
        window.addEventListener("drop", (event: Event) => {
            this.overrideEventDefaults(event);
        });
    }

    componentWillUnmount() {
        window.removeEventListener("dragover", this.overrideEventDefaults);
        window.removeEventListener("drop", this.overrideEventDefaults);
    }

    render() {
        return (
        <FileUploaderPresentationalComponent
            dragging={this.state.dragging}
            file={this.state.file}
            onSelectFileClick={this.onSelectFileClick}
            onDrag={this.overrideEventDefaults}
            onDragStart={this.overrideEventDefaults}
            onDragEnd={this.overrideEventDefaults}
            onDragOver={this.overrideEventDefaults}
            onDragEnter={this.dragenterListener}
            onDragLeave={this.dragleaveListener}
            onDrop={this.dropListener}>

            <input
                ref={el => (this.fileUploaderInput = el)}
                type="file"
                className={styles.file_uploader_input}
                onChange={this.onFileChanged}
            />
        </FileUploaderPresentationalComponent>
        );
    }
}