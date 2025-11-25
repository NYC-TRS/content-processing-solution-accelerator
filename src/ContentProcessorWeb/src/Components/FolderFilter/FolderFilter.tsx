import React, { useState, useEffect } from "react";
import { Combobox, Option, Button } from "@fluentui/react-components";
import { DismissRegular } from "@fluentui/react-icons";
import { useDispatch, useSelector, shallowEqual } from 'react-redux';
import { RootState, AppDispatch } from '../../store';
import { setFolderFilter, clearFolderFilter, fetchFolders } from '../../store/slices/leftPanelSlice';
import './FolderFilter.styles.scss';

interface FolderFilterProps {
  schemaId?: string;
}

const FolderFilter: React.FC<FolderFilterProps> = ({ schemaId }) => {
  const dispatch = useDispatch<AppDispatch>();

  const store = useSelector((state: RootState) => ({
    selectedFolders: state.leftPanel.folderFilter.selectedFolders,
    availableFolders: state.leftPanel.folderFilter.availableFolders,
    isLoading: state.leftPanel.folderFilter.isLoading,
  }), shallowEqual);

  const [selectedOptions, setSelectedOptions] = useState<string[]>([]);

  // Fetch folders when component mounts or schema changes
  useEffect(() => {
    dispatch(fetchFolders({ schemaId }));
  }, [schemaId, dispatch]);

  // Sync local state with Redux
  useEffect(() => {
    setSelectedOptions(store.selectedFolders);
  }, [store.selectedFolders]);

  const handleOptionSelect = (_ev: any, data: any) => {
    const newSelection = data.selectedOptions || [];
    setSelectedOptions(newSelection);
    dispatch(setFolderFilter(newSelection));
  };

  const handleClearFilter = () => {
    setSelectedOptions([]);
    dispatch(clearFolderFilter());
  };

  // Add "(Unassigned)" option for null folders
  const folderOptions = [
    '(Unassigned)',
    ...store.availableFolders
  ];

  const displayText = selectedOptions.length === 0
    ? "Filter by Folder (All)"
    : `${selectedOptions.length} folder${selectedOptions.length > 1 ? 's' : ''} selected`;

  return (
    <div className="folder-filter-container">
      <Combobox
        placeholder={displayText}
        multiselect
        selectedOptions={selectedOptions}
        onOptionSelect={handleOptionSelect}
        disabled={store.isLoading}
        aria-label="Filter by folder"
      >
        {folderOptions.map((folder) => (
          <Option key={folder} value={folder}>
            {folder}
          </Option>
        ))}
      </Combobox>

      {selectedOptions.length > 0 && (
        <Button
          appearance="subtle"
          onClick={handleClearFilter}
          size="small"
          icon={<DismissRegular />}
          title="Clear folder filter"
        >
          Clear
        </Button>
      )}
    </div>
  );
};

export default FolderFilter;
