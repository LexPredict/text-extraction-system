import { Component } from "react"
import { inject} from 'mobx-react';
import { Button } from 'antd';
import FileUpload from "../components/FileUpload"
import { IStoreComponent } from "../store";


type State = {
    file: File | null;
}

type FileUploaderProps = {
};

@inject('stores') export class PageParse extends Component<FileUploaderProps, State> {
    protected stores(): any {
        return (this.props as IStoreComponent).stores;
    }
    
    public onFileSelected = (file: File) => {
        const newState = {...this.state};
        newState.file = file;
        this.setState(newState);
        console.log('file selected');
    };

    public onUploadClicked = () => {
        if (!this.state) return;
        this.stores().upload.upload(this.state.file);
    }

    render() {
        return <>
            <h2>Parse document(s)</h2>
            <form>
                <FileUpload fileSelected={this.onFileSelected}></FileUpload>
            </form>
            <br/>
            <Button 
                type="primary" 
                onClick={() => this.onUploadClicked()}
                disabled={this.state && this.state.file ? false : true}
                >
                Upload Document
            </Button>
        </> 
    }   
}