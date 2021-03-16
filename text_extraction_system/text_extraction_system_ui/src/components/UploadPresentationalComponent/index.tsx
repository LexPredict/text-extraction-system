import styles from './UploadPresentationalComponent.module.css'; 


type PresentationalProps = {
    dragging: boolean;
    file: File | null;
    onSelectFileClick: () => void;
    onDrag: (event: React.DragEvent<HTMLDivElement>) => void;
    onDragStart: (event: React.DragEvent<HTMLDivElement>) => void;
    onDragEnd: (event: React.DragEvent<HTMLDivElement>) => void;
    onDragOver: (event: React.DragEvent<HTMLDivElement>) => void;
    onDragEnter: (event: React.DragEvent<HTMLDivElement>) => void;
    onDragLeave: (event: React.DragEvent<HTMLDivElement>) => void;
    onDrop: (event: React.DragEvent<HTMLDivElement>) => void;
  };
  
  
export const FileUploaderPresentationalComponent: React.FunctionComponent<PresentationalProps> = props => { 
  let uploaderClasses = styles.file_uploader;
  if (props.dragging) {
    uploaderClasses += styles.file_uploader_dragging;
  }

  const fileName = props.file ? props.file.name : "No File Selected";

  return (
    <div
      className={uploaderClasses}
      onDrag={props.onDrag}
      onDragStart={props.onDragStart}
      onDragEnd={props.onDragEnd}
      onDragOver={props.onDragOver}
      onDragEnter={props.onDragEnter}
      onDragLeave={props.onDragLeave}
      onDrop={props.onDrop}
    >
      <div className={styles.file_uploader_contents}>
        <span className={styles.file_uploader_file_name}>{fileName}</span>
        <span>Drag & Drop File</span>
        <span>or</span>
        <span onClick={props.onSelectFileClick}>
          Select File
        </span>
      </div>
      {props.children}
    </div>
  );
}