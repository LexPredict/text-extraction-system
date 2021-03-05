import { Menu } from 'antd';
import { Component } from 'react';
import { Link } from 'react-router-dom';
import React from 'react';

export class MenuItem {
    name: string;
    title?: string;
    url: string;
    children: Array<MenuItem>;
    
    constructor(
        name: string,
        title: string,
        url: string,
        children?: Array<MenuItem>) {
            this.name = name;
            this.title = title;
            this.url = url;
            this.children = children || Array<MenuItem>();
        }
}

type TopMenuProps = {
  rows: MenuItem[]
}

export class TopMenu extends Component<TopMenuProps> {
    constructor(props: TopMenuProps) {
        super(props)
    }
  
    render() {
        const path = window.location.pathname;
        let pageIndex = 0;
        this.props.rows.forEach((r, i) => {
            if (path.indexOf(r.url) >= 0) pageIndex = i;
        })

        return <>
            <Menu
                theme="dark"
                mode="horizontal"
                defaultSelectedKeys={[`${pageIndex + 1}`]}
                style={{ lineHeight: '64px' }}
                collapsedWidth="0">
                {this.props.rows.map((item, i) =>
                    <Menu.Item title={item.title} key={i+1}>
                        <Link to={item.url}>
                            <span>{item.name}</span>
                        </Link>                        
                    </Menu.Item>
                )}
            </Menu>
        </> 
    }   
}