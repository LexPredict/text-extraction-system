import { Component } from 'react';
import { inject, observer } from 'mobx-react';
import { IStoreComponent } from "../store";
import { Table, Pagination, Tag, Button } from 'antd';
import { formatDatetime } from "../entity/utils";
import { SortOrder } from 'antd/es/table/interface';


type State = {
}


type EmptyProps = {
};


@inject('stores') 
@observer export class PageTasks extends Component<EmptyProps, State> {
    constructor(props) {
        super(props);
    }
   
    protected stores(): any {
        return (this.props as IStoreComponent).stores;
    }

    onPaging(page: number, itemsOnPage: number): void {
        this.stores().tasks.updatePage(page, itemsOnPage);
    }

    toggleFullRequestId(sender: any) {
        const senderSpan = sender.target.parentElement.parentElement;
        const prefNode = senderSpan.childNodes[0];
        const idNode = senderSpan.childNodes[1];
        const spans = [prefNode, idNode];

        spans.forEach((e) => {
            if(e.style.display == 'inline') {
                e.style.display = 'none';
            }
            else {
                e.style.display = 'inline';
            }
        });
    }

    handleTableChange = (pagination, filters, sorter) => {
        // console.log(`${sorter.field}, ${sorter.order}`);
        this.stores().tasks.updateSorting(sorter.field, sorter.order);
    }

    render() {
        const tasks = this.stores().tasks.tasks;
        const requests = this.stores().requests.getRequests();
        console.log('There are ' + requests.length + ' requests');
        
        const columns = [
            {
                title: 'Request ID',
                dataIndex: 'id',
                key: 'id',
                render: (text, record) => {
                    const pref = text.substring(0, 8);
                    return <span>
                            <span style={{'display':'inline'}}>{pref}</span>
                            <span style={{'display':'none'}}>{text}</span>
                            <Button type="link" size="small" onClick={(s) => this.toggleFullRequestId(s)}>
                              ...
                            </Button>
                        </span>
                }
            },
            {
                title: 'Status',
                dataIndex: 'status',
                key: 'status',
                defaultSortOrder: 'status' as SortOrder,
                sorter: (a, b) => a - b,
                render: status => {
                    const color = status == 'DONE' ? 'green' : status == 'PENDING' ? 'gray' : 'red';
                    return <Tag color={color} key={status}>
                            {status}
                      </Tag>
                },
            },
            {
                title: 'File',
                dataIndex: 'fileName',
                key: 'fileName',
                sorter: (a, b) => a - b
            },
            {
                title: 'Started',
                dataIndex: 'started',
                key: 'started',
                render: started => {
                    return <span>{formatDatetime(started)}</span>
                },
                defaultSortOrder: 'descend' as SortOrder,
                sorter: (a, b) => a - b
            },
            {
                title: 'Download',
                key: 'id',
                dataIndex: 'id',
                render: (text, record) => {
                    if (record.status != 'DONE')
                        return <> - </>
                    return <>
                        <a href={`/api/v1/data_extraction_tasks/${record['id']}/results/extracted_plain_text.txt`}>.txt</a>
                        &nbsp;&nbsp;&nbsp;
                        <a href={`/api/v1/data_extraction_tasks/${record['id']}/results/packed_data.zip`}>.zip archive</a>
                    </>
                }
            }
        ];

        return <>
            <Table 
                dataSource={tasks.slice()} 
                columns={columns} 
                rowKey="id" 
                pagination={false} 
                onChange={(pagination, filters, sorter) => this.handleTableChange(pagination, filters, sorter)}>
            </Table>
            <Pagination 
                onChange={(p, pSize) => this.onPaging(p, pSize)}
                total={requests.length}>
            </Pagination>
        </> 
    }
}