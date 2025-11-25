import { TableRowId, TableRowData as RowStateBase, } from "@fluentui/react-components";
import { ListChildComponentProps } from "react-window";

export interface Item {
    fileName: { label: string; icon: JSX.Element };
    imported: { label: string };
    status: { label: string };
    processTime?: { label: string }; // Made optional - commented out in UI
    entityScore: { label: string };
    schemaScore: { label: string };
    processId: { label: string };
    lastModifiedBy: { label: string };
    file_mime_type: { label: string };
    confidence: {
        totalFields: number;
        zeroConfidenceCount: number;
        zeroConfidenceFields: string[];
    };
    folder: { label: string | null };
}

export interface TableRowData extends RowStateBase<Item> {
    onClick: (e: React.MouseEvent) => void;
    onKeyDown: (e: React.KeyboardEvent) => void;
    selected: boolean;
    appearance: "brand" | "none";
}

export interface ReactWindowRenderFnProps extends ListChildComponentProps {
    data: TableRowData[];
    style: any;
    index: number;
}

export interface GridComponentProps { }
