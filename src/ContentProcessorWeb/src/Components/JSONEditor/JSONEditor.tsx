import React, { useEffect, useState } from 'react'
import { JsonEditor, JsonEditorProps, githubDarkTheme } from 'json-edit-react'
import './JSONEditor.styles.scss'

import { useDispatch, useSelector, shallowEqual } from 'react-redux';
import { AppDispatch, RootState } from '../../store';
import { fetchContentJsonData, setModifiedResult } from '../../store/slices/centerPanelSlice';

import { SearchBox, Checkbox } from "@fluentui/react-components";

interface JSONEditorProps {
  processId?: string | null;
}

const JSONEditor: React.FC<JSONEditorProps> = () => {
  const [jsonData, setJsonData] = React.useState({})
  const [isFocused, setIsFocused] = useState(false);
  const dispatch = useDispatch<AppDispatch>();
  const [searchText, setSearchText] = useState('');
  const searchBoxRef = React.useRef<HTMLDivElement | null>(null);
  const [hideNulls, setHideNulls] = useState<boolean>(() => {
    const saved = localStorage.getItem('jsonEditor_hideNulls');
    return saved ? JSON.parse(saved) : false;
  });

  const store = useSelector((state: RootState) => ({
    processId: state.leftPanel.processId,
    contentData: state.centerPanel.contentData,
    cLoader: state.centerPanel.cLoader,
    cError: state.centerPanel.cError,
    isJSONEditorSearchEnabled: state.centerPanel.isJSONEditorSearchEnabled
  }), shallowEqual);

  // Save hideNulls preference to localStorage
  useEffect(() => {
    localStorage.setItem('jsonEditor_hideNulls', JSON.stringify(hideNulls));
  }, [hideNulls]);

  // Recursively filter null, undefined, and empty string values from object
  const filterNullValues = (obj: any): any => {
    if (obj === null || obj === undefined || obj === '') {
      return undefined;
    }

    if (Array.isArray(obj)) {
      const filtered = obj.map(item => filterNullValues(item)).filter(item => item !== undefined);
      return filtered.length > 0 ? filtered : undefined;
    }

    if (typeof obj === 'object') {
      const filtered: any = {};
      let hasValidFields = false;

      for (const [key, value] of Object.entries(obj)) {
        const filteredValue = filterNullValues(value);
        if (filteredValue !== undefined) {
          filtered[key] = filteredValue;
          hasValidFields = true;
        }
      }

      return hasValidFields ? filtered : undefined;
    }

    return obj;
  };

  useEffect(() => {
    if (!store.cLoader) {
      if (Object.keys(store.contentData).length > 0) {
        const formattedJson = store.contentData.result;
        let data = { ...formattedJson };

        // Apply null filtering if enabled
        if (hideNulls) {
          data = filterNullValues(data) || {};
        }

        setJsonData(data);
      } else {
        setJsonData({})
      }
    }

  }, [store.contentData, hideNulls])

  const onUpdateHandle = (newData: any) => {
    dispatch(setModifiedResult(newData));
  }

  const handleFocus = () => setIsFocused(true);
  const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
    const newFocusTarget = e.relatedTarget as HTMLElement | null;
    if (
      searchBoxRef.current &&
      newFocusTarget &&
      searchBoxRef.current.contains(newFocusTarget)
    ) {
      return;
    }

    setIsFocused(false);
  };

  return (
    <>{
      store.cLoader ? <div className={"JSONEditorLoader"}><p>Loading...</p></div> :
        Object.keys(jsonData).length == 0 ? <p style={{ textAlign: 'center' }}>No data available</p> :
          <div className="JSONEditor-container">
            {store.isJSONEditorSearchEnabled &&
              <div className="JSONEditor-searchDiv">
                <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: '12px' }} ref={searchBoxRef}>
                  <Checkbox
                    label="Hide null values"
                    checked={hideNulls}
                    onChange={(_, data) => setHideNulls(data.checked === true)}
                  />
                  <SearchBox
                    size="small"
                    placeholder="Search"
                    onFocus={handleFocus}
                    onBlur={handleBlur}
                    value={searchText}
                    onChange={(_, data) => { setIsFocused(true); setSearchText(data.value) }}
                    style={{
                      width: isFocused ? '200px' : '100px',
                      transition: 'width 0.3s ease',
                    }}
                  />
                </div></div>}
            <div className="JSONEditor-contentDiv">
              <JsonEditor
                data={jsonData}
                className='JSONEditorClass'
                rootName="extracted_result"
                searchText={searchText}
                searchFilter={"all"}
                searchDebounceTime={300}
                theme={[{
                  styles: {
                    container: {
                      width: '89%',
                      minWidth: '100%',
                      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, "Apple Color Emoji", "Segoe UI Emoji", sans-serif',
                      fontSize: '14px',
                      paddingTop: '0px'
                    },
                  }
                }]}
                onUpdate={({ newData }) => {
                  onUpdateHandle(newData)
                }}
                //setData={ setJsonData } // optional
                // restrictEdit={({ key, path, level, index, value, size, parentData, fullData, collapsed }) => {
                //   return !path.includes('extracted_result')
                // }
                // }
                restrictDelete={true}
              />
            </div>
          </div>
    }</>
  )
}

export default JSONEditor;

