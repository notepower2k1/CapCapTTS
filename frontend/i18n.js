// i18n.js — Language localization for CapCap TTS

const TRANSLATIONS = {
	en: {
		// Header
		dict_btn: 'Dict',
		pause_btn: 'Pause',
		history_btn: 'History',
		resource_btn: 'Resources',
		help_btn: 'Guide',
		reset_btn: 'Reset',
		theme_btn_title: 'Toggle dark mode',
		lang_btn_title: 'Chuyển sang Tiếng Việt / Switch language',

		// Input area
		drop_hint: 'Drop <span>.txt</span> <span>.md</span> files or paste text',
		btn_clear: 'Clear',
		btn_save_draft: 'Save Draft',
		btn_insert_pause: '+ Insert pause',
		chk_normalize: 'Vietnamese normalize',
		hint_normalize: 'Converts numbers, dates, currencies & abbreviations to spoken words',
		btn_inline_dict: 'Dictionary',
		tip_manage_dict: 'Manage dictionary (Acronyms & foreign words)',
		hint_normalize_off: '(Disabled — Dictionary and number reading rules will not apply)',
		dict_disabled_title: 'Enable Vietnamese normalize to use dictionary',
		hint_clean: 'Removes emojis, URLs & unsupported symbols before synthesis',
		hint_split_mode: 'Divides long text into smaller segments for smooth AI speech',
		hint_m_fade: 'Prevents popping & clicking sounds at sentence boundaries',
		hint_m_vol: 'Balances loudness across all segments evenly',
		hint_m_crossfade: 'Smooth 50ms overlap transition between adjacent sentences',
		hint_m_comp: 'Produces a warmer, richer, and podcast-ready voice tone',
		chk_clean: 'Auto clean text',
		chk_norm_audio: 'Normalize volume',
		chk_split: 'Split segments',
		opt_split_default: 'Default (paragraph + sentence)',
		opt_split_sentence: 'By sentence',
		opt_split_paragraph: 'By paragraph',
		opt_split_custom: 'Custom (by blank line)',

		// Voice & settings
		tier_low: 'Low',
		tier_turbo: 'Medium-Low',
		tier_medium: 'Medium',
		tier_high: 'High',
		btn_change_voice: 'Change',
		btn_new_voice: '+ New',
		btn_preview: 'Preview',
		btn_generate: 'Generate',
		lbl_adv: 'Advanced',
		lbl_speed: 'Speed',
		lbl_volume: 'Volume',
		lbl_model_config_f5: 'Model Config — Medium (F5)',
		lbl_model_config_omni: 'Model Config — High (OmniVoice)',
		lbl_voice_match: 'Voice Match',
		tip_voice_match: 'Higher = voice matches reference more closely. Lower = more variation.',
		lbl_quality: 'Quality',
		tip_quality_steps: 'More steps = better quality but slower.',
		lbl_rhythm: 'Rhythm',
		tip_rhythm: 'Controls speech rhythm. -1.0 is default.',

		// Progress
		generating_audio: 'Generating audio...',
		splitting: 'Splitting...',
		merging_audio: 'Merging audio...',
		btn_cancel: 'Cancel',

		// Segments panel
		title_segments: 'Text Segments',
		saved: 'Saved',
		filter_all: 'All',
		filter_done: 'Done',
		filter_warning: 'Warning',
		filter_failed: 'Failed',
		filter_processing: 'Processing',
		btn_retry_failed: 'Retry Failed',
		btn_retry_warning: 'Retry Warning',
		btn_collapse_all: 'Collapse All',
		btn_expand_failed: 'Expand Failed',
		empty_segments: 'Enter text and click Generate to see segments',
		btn_merge_download: 'Merge & Download All',
		btn_download_all: 'Download All',

		// Final audio bar
		final_audio_title: 'Final Audio',
		tip_hide: 'Hide',
		tip_volume: 'Volume',
		tip_play: 'Play',
		tip_pause: 'Pause',
		btn_export: 'Export',
		btn_remerge: 'Re-merge',
		mastering_title: 'Mastering Options',
		mastering_fade: 'Anti-click Fade (8ms/12ms)',
		mastering_vol_match: 'Volume Matching',
		mastering_crossfade: 'Crossfade (50ms)',
		mastering_compressor: 'Voice Compressor',
		toast_remerged: 'Re-merged audio with selected mastering options',
		btn_apply_remerge: 'Apply & Re-merge',

		// Dict Modal
		dict_title: 'Dictionary',
		dict_tab_acronyms: 'Acronyms',
		dict_tab_words: 'Words',
		th_acronym: 'Acronym',
		th_word: 'Word',
		th_pronunciation: 'Pronunciation',
		btn_add_entry: '+ Add entry',
		btn_close: 'Close',

		// Pause Modal
		pause_title: 'Punctuation Pauses',
		pause_desc: 'Silence after punctuation (seconds)',
		lbl_linebreak: 'Line break',
		btn_save: 'Save',

		// Voice Select Modal
		voice_modal_title: 'Select Voice',
		gender_all: 'All Genders',
		gender_male: 'Male',
		gender_female: 'Female',
		type_all: 'All Types',
		type_default: 'Default',
		type_clone: 'Clone',

		// History Modal
		history_title: 'History',
		btn_clear_all: 'Clear All',
		history_empty: 'No history yet',

		// Voice Lab Modal
		voice_lab_title: 'Voice Lab',
		lbl_voice_name: 'Voice Name',
		ph_voice_name: 'e.g. my_voice_1',
		lbl_gender: 'Gender',
		lbl_desc: 'Description',
		ph_desc: 'No description',
		lbl_ref_audio: 'Reference Audio',
		lbl_ref_text: 'Reference Text',
		ph_ref_text: 'What was said in the reference audio...',
		btn_save_voice: 'Save Voice',
		btn_uploading: 'Uploading...',

		// Resource Modal
		resource_title: 'Resources',
		tab_download: 'Download',
		tab_load_models: 'Load Models',
		lbl_storage_path: 'Resource Storage Location',
		btn_open_folder: 'Open Folder',
		btn_reset_default: 'Default',
		btn_save_path: 'Save',
		hint_storage_path: 'All downloaded voice models (Piper, VieNeu, F5-TTS, OmniVoice) are saved to and read from this directory.',
		toast_storage_updated: 'Resource storage path updated!',
		lbl_use_mirror: 'Fast Mirror download (hf-mirror.com)',
		hint_use_mirror: '(Faster when international connection is slow)',
		toast_mirror_enabled: 'Enabled Fast Mirror (hf-mirror.com)',
		toast_mirror_disabled: 'Disabled Fast Mirror',
		toast_folder_opened: 'Opened folder',
		btn_manual_download: 'Manual',
		manual_guide_title: 'Manual Download Guide:',
		manual_step_link: 'Download files using browser or IDM at:',
		manual_step_dir: 'Place downloaded files into folder:',
		btn_open_target_dir: 'Open Folder',
		manual_step_done: 'Once copied, click',
		btn_recheck: 'Recheck',
		manual_step_recheck: 'to verify.',
		download_btn: 'Download',
		downloading_btn: 'Downloading…',
		downloaded_badge: 'Downloaded',
		load_model_btn: 'Load Model',
		loading_btn: 'Loading...',
		loaded_btn: 'Loaded',
		not_loaded_badge: 'Not Loaded',

		// Help Modal
		help_title: 'How to Use',

		// Dynamic units & labels
		unit_chars: 'chars',
		unit_words: 'words',
		unit_audio: 'audio',
		unit_segments: 'segments',
		unit_files: 'files',
		page: 'Page',
		label_voice: 'Voice:',
		filter_gender: 'Gender',
		filter_type: 'Type',
		clone_voices: 'Clone Voices',
		default_voices: 'Default Voices',
		segment_prefix: 'Segment ',
		edit: 'Edit',
		retry: 'Retry',
		apply_to_all: 'Apply to all',
		process_all: 'Process All',
		status_done: 'Done',
		status_processing: 'Processing...',
		status_error: 'Error',
		status_pending: 'Pending',
		generated_audio: 'Generated Audio',
		audio_ready_hint: '✓ Audio ready — see Final Audio bar below',
		generating_dots: 'Generating...',
		queued_dots: 'Queued...',
		no_segments_yet: 'No segments yet. Generate audio to begin.',
		no_voices_match: 'No voices match the filter',
		edit_description: 'Edit description',
		delete_voice: 'Delete voice',
		badge_clone: 'CLONE',
		badge_default: 'DEFAULT',

		// Toasts & Dialogs
		confirm_clear_all: 'Clear all text?',
		toast_draft_saved: 'Draft saved',
		confirm_delete_voice: 'Delete this cloned voice?',
		toast_voice_deleted: 'Voice deleted',
		err_delete_default_voice: 'Cannot delete default voice',
		prompt_edit_desc: 'Edit description:',
		toast_desc_updated: 'Description updated',
		err_update_desc: 'Failed to update description',
		confirm_reset: 'Reset this session? All generated audio will be deleted.',
		confirm_cancel: 'Cancel generation?',
		toast_gen_cancelled: 'Generation cancelled',
		confirm_clear_hist: 'Clear all history and audio files?',
		toast_hist_cleared: 'History cleared',
		err_enter_text: 'Enter some text',
		err_select_voice: 'Select a voice',
		toast_both_req: 'Both fields required',
		toast_saved: 'Saved',
		toast_deleted: 'Deleted',
		alert_fill_all_clone: 'Fill all fields and select an audio file',
		toast_no_seg_download: 'No segments to download',
		toast_prep_zip: 'Preparing zip...',
		toast_text_updated: 'Text updated',
		merging_dots: 'Merging...',
		toast_config_saved_prefix: 'Config saved for ',
		toast_config_applied_all: 'Config applied to all pending files',
		toast_switched_lang: 'Switched to English'
	},

	vi: {
		// Header
		dict_btn: 'Từ điển',
		pause_btn: 'Dấu câu',
		history_btn: 'Lịch sử',
		resource_btn: 'Tài nguyên',
		help_btn: 'Hướng dẫn',
		reset_btn: 'Đặt lại',
		theme_btn_title: 'Bật/tắt chế độ tối',
		lang_btn_title: 'Switch to English / Đổi ngôn ngữ',

		// Input area
		drop_hint: 'Kéo thả file <span>.txt</span> <span>.md</span> hoặc dán văn bản',
		btn_clear: 'Xóa',
		btn_save_draft: 'Lưu nháp',
		btn_insert_pause: '+ Chèn nghỉ',
		chk_normalize: 'Chuẩn hóa tiếng Việt',
		hint_normalize: 'Tự đổi số, ngày tháng, tiền tệ, viết tắt thành chữ đọc',
		btn_inline_dict: 'Từ điển',
		tip_manage_dict: 'Quản lý từ điển (Từ viết tắt & từ mượn)',
		hint_normalize_off: '(Đang tắt — Toàn bộ từ điển và quy tắc đọc số sẽ không áp dụng)',
		dict_disabled_title: 'Cần bật Chuẩn hóa tiếng Việt để dùng từ điển',
		hint_clean: 'Xóa emoji, link web & ký tự lạ để tránh AI đọc vấp/rè',
		hint_split_mode: 'Chia văn bản dài thành các đoạn nhỏ để AI đọc mượt mà',
		hint_m_fade: 'Khử tiếng lụp bụp/nổ li ti ở điểm đầu và đuôi câu',
		hint_m_vol: 'Kéo âm lượng tất cả các câu về mức đồng đều cả bài',
		hint_m_crossfade: 'Chuyển tiếp êm ái, đan xen 50ms giữa 2 câu liền kề',
		hint_m_comp: 'Nén âm nhẹ giúp giọng đọc ấm, dày và chuyên nghiệp hơn',
		chk_clean: 'Tự động làm sạch',
		chk_norm_audio: 'Cân bằng âm lượng',
		chk_split: 'Chia đoạn',
		opt_split_default: 'Mặc định (đoạn + câu)',
		opt_split_sentence: 'Theo câu',
		opt_split_paragraph: 'Theo đoạn',
		opt_split_custom: 'Tùy chỉnh (theo dòng trống)',

		// Voice & settings
		tier_low: 'Nhẹ (Low)',
		tier_turbo: 'Trung bình-Thấp (Medium-Low)',
		tier_medium: 'Vừa (Medium)',
		tier_high: 'Cao (High)',
		btn_change_voice: 'Đổi',
		btn_new_voice: '+ Tạo mới',
		btn_preview: 'Nghe thử',
		btn_generate: 'Tạo giọng nói',
		lbl_adv: 'Nâng cao',
		lbl_speed: 'Tốc độ',
		lbl_volume: 'Âm lượng',
		lbl_model_config_f5: 'Cấu hình mô hình — Vừa (F5)',
		lbl_model_config_omni: 'Cấu hình mô hình — Cao (OmniVoice)',
		lbl_voice_match: 'Độ giống giọng',
		tip_voice_match: 'Cao hơn = giống mẫu hơn. Thấp hơn = đa dạng hơn.',
		lbl_quality: 'Chất lượng',
		tip_quality_steps: 'Càng nhiều bước = chất lượng càng cao nhưng chậm hơn.',
		lbl_rhythm: 'Nhịp điệu',
		tip_rhythm: 'Điều chỉnh nhịp điệu phát âm. -1.0 là mặc định.',

		// Progress
		generating_audio: 'Đang tạo âm thanh...',
		splitting: 'Đang phân đoạn...',
		merging_audio: 'Đang ghép âm thanh...',
		btn_cancel: 'Hủy',

		// Segments panel
		title_segments: 'Các đoạn văn bản',
		saved: 'Đã lưu',
		filter_all: 'Tất cả',
		filter_done: 'Xong',
		filter_warning: 'Cảnh báo',
		filter_failed: 'Lỗi',
		filter_processing: 'Đang xử lý',
		btn_retry_failed: 'Thử lại lỗi',
		btn_retry_warning: 'Thử lại cảnh báo',
		btn_collapse_all: 'Thu gọn tất cả',
		btn_expand_failed: 'Mở rộng đoạn lỗi',
		empty_segments: 'Nhập văn bản và nhấn "Tạo giọng nói" để xem các đoạn',
		btn_merge_download: 'Ghép & Tải tất cả',
		btn_download_all: 'Tải tất cả (ZIP)',

		// Final audio bar
		final_audio_title: 'File hoàn chỉnh',
		tip_hide: 'Ẩn',
		tip_volume: 'Âm lượng',
		tip_play: 'Phát',
		tip_pause: 'Tạm dừng',
		btn_export: 'Xuất file',
		btn_remerge: 'Ghép lại',
		mastering_title: 'Tùy chọn Hậu kỳ (Mastering)',
		mastering_fade: 'Fade mép chống nổ (8ms/12ms)',
		mastering_vol_match: 'Cân bằng âm lượng đều bài',
		mastering_crossfade: 'Nối đan xen (Crossfade 50ms)',
		mastering_compressor: 'Nén dải động (Voice Compressor)',
		toast_remerged: 'Đã ghép lại âm thanh với tùy chọn đã chọn',
		btn_apply_remerge: 'Áp dụng & Tạo lại',

		// Dict Modal
		dict_title: 'Từ điển phát âm',
		dict_tab_acronyms: 'Từ viết tắt',
		dict_tab_words: 'Từ ngữ',
		th_acronym: 'Từ viết tắt',
		th_word: 'Từ gốc',
		th_pronunciation: 'Cách phát âm',
		btn_add_entry: '+ Thêm từ',
		btn_close: 'Đóng',

		// Pause Modal
		pause_title: 'Tạm dừng theo dấu câu',
		pause_desc: 'Thời gian nghỉ sau dấu câu (giây)',
		lbl_linebreak: 'Xuống dòng',
		btn_save: 'Lưu',

		// Voice Select Modal
		voice_modal_title: 'Chọn giọng đọc',
		gender_all: 'Tất cả giới tính',
		gender_male: 'Nam',
		gender_female: 'Nữ',
		type_all: 'Tất cả loại',
		type_default: 'Mặc định',
		type_clone: 'Nhân bản',

		// History Modal
		history_title: 'Lịch sử tạo',
		btn_clear_all: 'Xóa tất cả',
		history_empty: 'Chưa có lịch sử nào',

		// Voice Lab Modal
		voice_lab_title: 'Phòng nhân bản giọng',
		lbl_voice_name: 'Tên giọng đọc',
		ph_voice_name: 'vd: giong_doc_1',
		lbl_gender: 'Giới tính',
		lbl_desc: 'Mô tả',
		ph_desc: 'Chưa có mô tả',
		lbl_ref_audio: 'File âm thanh mẫu',
		lbl_ref_text: 'Văn bản mẫu',
		ph_ref_text: 'Nội dung nói trong file âm thanh mẫu...',
		btn_save_voice: 'Lưu giọng đọc',
		btn_uploading: 'Đang tải lên...',

		// Resource Modal
		resource_title: 'Quản lý tài nguyên',
		tab_download: 'Tải về',
		tab_load_models: 'Nạp mô hình',
		lbl_storage_path: 'Thư mục lưu tài nguyên',
		btn_open_folder: 'Mở thư mục',
		btn_reset_default: 'Mặc định',
		btn_save_path: 'Lưu',
		hint_storage_path: 'Toàn bộ mô hình tải về (Piper, VieNeu, F5-TTS, OmniVoice) sẽ được lưu và đọc từ thư mục này.',
		toast_storage_updated: 'Đã cập nhật nơi lưu tài nguyên!',
		lbl_use_mirror: 'Tải tăng tốc qua máy chủ Mirror (hf-mirror.com)',
		hint_use_mirror: '(Tải nhanh hơn nếu mạng quốc tế bị chậm)',
		toast_mirror_enabled: 'Đã bật Mirror tăng tốc (hf-mirror.com)',
		toast_mirror_disabled: 'Đã tắt Mirror tăng tốc',
		toast_folder_opened: 'Đã mở thư mục',
		btn_manual_download: 'Tải thủ công',
		manual_guide_title: 'Hướng dẫn tải thủ công:',
		manual_step_link: 'Tải trực tiếp bằng trình duyệt hoặc IDM tại:',
		manual_step_dir: 'Chép các file vào thư mục:',
		btn_open_target_dir: 'Mở thư mục',
		manual_step_done: 'Sau khi chép xong, bấm',
		btn_recheck: 'Kiểm tra lại',
		manual_step_recheck: 'để hệ thống ghi nhận.',
		download_btn: 'Tải về',
		downloading_btn: 'Đang tải…',
		downloaded_badge: 'Đã tải',
		load_model_btn: 'Nạp mô hình',
		loading_btn: 'Đang nạp...',
		loaded_btn: 'Đã nạp',
		not_loaded_badge: 'Chưa nạp',

		// Help Modal
		help_title: 'Hướng dẫn sử dụng',

		// Dynamic units & labels
		unit_chars: 'ký tự',
		unit_words: 'từ',
		unit_audio: 'âm thanh',
		unit_segments: 'đoạn',
		unit_files: 'tệp',
		page: 'Trang',
		label_voice: 'Giọng:',
		filter_gender: 'Giới tính',
		filter_type: 'Loại',
		clone_voices: 'Giọng nhân bản',
		default_voices: 'Giọng mặc định',
		segment_prefix: 'Đoạn ',
		edit: 'Sửa',
		retry: 'Thử lại',
		apply_to_all: 'Áp dụng tất cả',
		process_all: 'Xử lý tất cả',
		status_done: 'Xong',
		status_processing: 'Đang xử lý...',
		status_error: 'Lỗi',
		status_pending: 'Đang chờ',
		generated_audio: 'Âm thanh đã tạo',
		audio_ready_hint: '✓ Âm thanh đã sẵn sàng — xem thanh phát bên dưới',
		generating_dots: 'Đang tạo...',
		queued_dots: 'Đang chờ...',
		no_segments_yet: 'Chưa có đoạn nào. Hãy tạo giọng nói để bắt đầu.',
		no_voices_match: 'Không có giọng đọc nào khớp bộ lọc',
		edit_description: 'Sửa mô tả',
		delete_voice: 'Xóa giọng đọc',
		badge_clone: 'NHÂN BẢN',
		badge_default: 'MẶC ĐỊNH',

		// Toasts & Dialogs
		confirm_clear_all: 'Xóa toàn bộ văn bản?',
		toast_draft_saved: 'Đã lưu bản nháp',
		confirm_delete_voice: 'Xóa giọng nhân bản này?',
		toast_voice_deleted: 'Đã xóa giọng đọc',
		err_delete_default_voice: 'Không thể xóa giọng mặc định',
		prompt_edit_desc: 'Sửa mô tả:',
		toast_desc_updated: 'Đã cập nhật mô tả',
		err_update_desc: 'Cập nhật mô tả thất bại',
		confirm_reset: 'Đặt lại phiên làm việc? Toàn bộ âm thanh đã tạo sẽ bị xóa.',
		confirm_cancel: 'Hủy quá trình tạo?',
		toast_gen_cancelled: 'Đã hủy quá trình tạo',
		confirm_clear_hist: 'Xóa toàn bộ lịch sử và file âm thanh?',
		toast_hist_cleared: 'Đã xóa lịch sử',
		err_enter_text: 'Vui lòng nhập văn bản',
		err_select_voice: 'Vui lòng chọn giọng đọc',
		toast_both_req: 'Vui lòng điền cả 2 trường',
		toast_saved: 'Đã lưu',
		toast_deleted: 'Đã xóa',
		alert_fill_all_clone: 'Vui lòng điền đầy đủ các trường và chọn file âm thanh mẫu',
		toast_no_seg_download: 'Không có đoạn nào để tải về',
		toast_prep_zip: 'Đang chuẩn bị file zip...',
		toast_text_updated: 'Đã cập nhật văn bản',
		merging_dots: 'Đang ghép...',
		toast_config_saved_prefix: 'Đã lưu cấu hình cho ',
		toast_config_applied_all: 'Đã áp dụng cấu hình cho tất cả file chờ',
		toast_switched_lang: 'Đã chuyển sang Tiếng Việt'
	}
};

let CURRENT_LANG = localStorage.getItem('capcap_lang') || 'vi';

function t(key, fallback = '') {
	if (TRANSLATIONS[CURRENT_LANG] && TRANSLATIONS[CURRENT_LANG][key] !== undefined) {
		return TRANSLATIONS[CURRENT_LANG][key];
	}
	if (TRANSLATIONS['en'] && TRANSLATIONS['en'][key] !== undefined) {
		return TRANSLATIONS['en'][key];
	}
	return fallback || key;
}

function applyTranslations(lang) {
	CURRENT_LANG = lang || CURRENT_LANG;
	localStorage.setItem('capcap_lang', CURRENT_LANG);
	document.documentElement.setAttribute('lang', CURRENT_LANG);

	// Update textContent / innerHTML for elements with data-i18n
	document.querySelectorAll('[data-i18n]').forEach(el => {
		const key = el.getAttribute('data-i18n');
		const translated = t(key);
		if (translated) {
			if (translated.includes('<') && translated.includes('>')) {
				el.innerHTML = translated;
			} else {
				el.textContent = translated;
			}
		}
	});

	// Update placeholders
	document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
		const key = el.getAttribute('data-i18n-placeholder');
		const translated = t(key);
		if (translated) el.placeholder = translated;
	});

	// Update titles / tooltips
	document.querySelectorAll('[data-i18n-title]').forEach(el => {
		const key = el.getAttribute('data-i18n-title');
		const translated = t(key);
		if (translated) el.title = translated;
	});

	// Update Language Toggle button
	const langBtn = document.getElementById('langBtn');
	if (langBtn) {
		const langLabel = document.getElementById('langLabel');
		if (langLabel) {
			langLabel.textContent = CURRENT_LANG.toUpperCase();
		} else {
			langBtn.textContent = CURRENT_LANG.toUpperCase();
		}
		langBtn.title = t('lang_btn_title');
	}
}

function toggleLanguage() {
	const nextLang = CURRENT_LANG === 'vi' ? 'en' : 'vi';
	applyTranslations(nextLang);
	if (typeof updateCharCount === 'function') updateCharCount();
	if (typeof updateVoiceLabel === 'function') updateVoiceLabel();
	if (typeof renderCurrentVoiceTab === 'function') renderCurrentVoiceTab();
	if (typeof renderChunks === 'function' && typeof CHUNK_DATA !== 'undefined') renderChunks(CHUNK_DATA);
	if (typeof renderFileQueue === 'function') renderFileQueue();
	const resModal = document.getElementById('resourceModal');
	if (resModal && !resModal.classList.contains('hidden')) {
		const activeTab = document.querySelector('#resourceModal .dict-tab.active');
		if (activeTab && activeTab.dataset.rtab === 'models') {
			if (typeof loadModelsTab === 'function') loadModelsTab();
		} else {
			if (typeof loadDownloadTab === 'function') loadDownloadTab();
		}
	}
	if (typeof showToast === 'function') showToast(t('toast_switched_lang'));
}

// Expose globally
window.t = t;
window.applyTranslations = applyTranslations;
window.toggleLanguage = toggleLanguage;
window.getLang = () => CURRENT_LANG;

document.addEventListener('DOMContentLoaded', () => {
	applyTranslations(CURRENT_LANG);
});
