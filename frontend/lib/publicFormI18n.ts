export type PublicFormLanguage = "es" | "en" | "pt" | "ko";

type PublicFormCopy = {
  chooseLanguage: string;
  loadingForm: string;
  loadError: string;
  unavailableTitle: string;
  retry: string;
  inactive: string;
  notOpenYet: string;
  closed: string;
  notFound: string;
  unavailableDefault: string;
  submitError: string;
  successTitle: string;
  bikeZoneCode: string;
  bikeZoneInstruction: string;
  responseCode: string;
  submitting: string;
  selectPlaceholder: string;
  yes: string;
  no: string;
};

const COPY: Record<PublicFormLanguage, PublicFormCopy> = {
  es: {
    chooseLanguage: "Elige tu idioma para continuar",
    loadingForm: "Cargando formulario...",
    loadError: "No se pudo cargar el formulario.",
    unavailableTitle: "Formulario no disponible",
    retry: "Reintentar",
    inactive: "Este formulario no está abierto para recibir respuestas en este momento.",
    notOpenYet: "Este formulario todavía no está abierto. Intenta nuevamente cuando comience el periodo de respuestas.",
    closed: "Este formulario ya cerró y no acepta nuevas respuestas.",
    notFound: "El enlace no corresponde a un formulario público disponible.",
    unavailableDefault: "No pudimos cargar este formulario. Revisa el enlace o intenta nuevamente más tarde.",
    submitError: "No se pudo enviar el formulario.",
    successTitle: "Respuesta recibida",
    bikeZoneCode: "Código Bike Zone",
    bikeZoneInstruction: "Usa este código para check-in y check-out.",
    responseCode: "Código de respuesta",
    submitting: "Enviando...",
    selectPlaceholder: "Selecciona",
    yes: "Sí",
    no: "No",
  },
  en: {
    chooseLanguage: "Choose your language to continue",
    loadingForm: "Loading form...",
    loadError: "The form could not be loaded.",
    unavailableTitle: "Form unavailable",
    retry: "Try again",
    inactive: "This form is not currently open for responses.",
    notOpenYet: "This form is not open yet. Please try again when the response period begins.",
    closed: "This form is closed and no longer accepts responses.",
    notFound: "This link does not match an available public form.",
    unavailableDefault: "We could not load this form. Check the link or try again later.",
    submitError: "The form could not be submitted.",
    successTitle: "Response received",
    bikeZoneCode: "Bike Zone code",
    bikeZoneInstruction: "Use this code for check-in and check-out.",
    responseCode: "Response code",
    submitting: "Submitting...",
    selectPlaceholder: "Select",
    yes: "Yes",
    no: "No",
  },
  pt: {
    chooseLanguage: "Escolha seu idioma para continuar",
    loadingForm: "Carregando formulário...",
    loadError: "Não foi possível carregar o formulário.",
    unavailableTitle: "Formulário indisponível",
    retry: "Tentar novamente",
    inactive: "Este formulário não está aberto para receber respostas neste momento.",
    notOpenYet: "Este formulário ainda não está aberto. Tente novamente quando o período de respostas começar.",
    closed: "Este formulário foi encerrado e não aceita novas respostas.",
    notFound: "O link não corresponde a um formulário público disponível.",
    unavailableDefault: "Não foi possível carregar este formulário. Verifique o link ou tente novamente mais tarde.",
    submitError: "Não foi possível enviar o formulário.",
    successTitle: "Resposta recebida",
    bikeZoneCode: "Código Bike Zone",
    bikeZoneInstruction: "Use este código para check-in e check-out.",
    responseCode: "Código da resposta",
    submitting: "Enviando...",
    selectPlaceholder: "Selecione",
    yes: "Sim",
    no: "Não",
  },
  ko: {
    chooseLanguage: "계속하려면 언어를 선택하세요",
    loadingForm: "양식을 불러오는 중...",
    loadError: "양식을 불러올 수 없습니다.",
    unavailableTitle: "양식을 사용할 수 없습니다",
    retry: "다시 시도",
    inactive: "현재 이 양식은 응답을 받고 있지 않습니다.",
    notOpenYet: "아직 이 양식의 응답 기간이 시작되지 않았습니다. 응답 기간이 시작되면 다시 시도하세요.",
    closed: "이 양식은 마감되어 더 이상 응답을 받지 않습니다.",
    notFound: "이 링크에 해당하는 공개 양식을 찾을 수 없습니다.",
    unavailableDefault: "양식을 불러올 수 없습니다. 링크를 확인하거나 나중에 다시 시도하세요.",
    submitError: "양식을 제출할 수 없습니다.",
    successTitle: "응답이 접수되었습니다",
    bikeZoneCode: "Bike Zone 코드",
    bikeZoneInstruction: "체크인 및 체크아웃 시 이 코드를 사용하세요.",
    responseCode: "응답 코드",
    submitting: "제출 중...",
    selectPlaceholder: "선택하세요",
    yes: "예",
    no: "아니요",
  },
};

const FIELD_LABELS: Record<string, Record<PublicFormLanguage, string>> = {
  event_name: { es: "Nombre del evento", en: "Event name", pt: "Nome do evento", ko: "이벤트 이름" },
  venue_name: { es: "Nombre del venue / recinto", en: "Venue", pt: "Local / recinto", ko: "장소" },
  full_name: { es: "Nombre completo", en: "Full name", pt: "Nome completo", ko: "성명" },
  email: { es: "Correo electrónico", en: "Email", pt: "E-mail", ko: "이메일" },
  phone: { es: "Teléfono", en: "Phone", pt: "Telefone", ko: "전화번호" },
  company: { es: "Empresa", en: "Company", pt: "Empresa", ko: "회사" },
  country_origin: { es: "País de origen", en: "Country of origin", pt: "País de origem", ko: "출신 국가" },
  country_residence: { es: "País de residencia", en: "Country of residence", pt: "País de residência", ko: "거주 국가" },
  residence_region: { es: "Región de residencia", en: "Region of residence", pt: "Região de residência", ko: "거주 지역" },
  residence_commune: { es: "Comuna de residencia", en: "Commune of residence", pt: "Comuna de residência", ko: "거주 코뮌" },
  transport_mode: { es: "Tipo de transporte utilizado para llegar", en: "Type of transport used to arrive", pt: "Tipo de transporte utilizado para chegar", ko: "이용한 교통수단" },
  bike_brand: { es: "Marca de bicicleta", en: "Bike brand", pt: "Marca da bicicleta", ko: "자전거 브랜드" },
  bike_model: { es: "Modelo de bicicleta", en: "Bike model", pt: "Modelo da bicicleta", ko: "자전거 모델" },
  bike_color: { es: "Color de bicicleta", en: "Bike color", pt: "Cor da bicicleta", ko: "자전거 색상" },
  event_ticket_number: { es: "Número de ticket", en: "Ticket number", pt: "Número do ingresso", ko: "티켓 번호" },
  comments: { es: "Comentarios", en: "Comments", pt: "Comentários", ko: "의견" },
};

const OPTION_LABELS: Record<string, Record<PublicFormLanguage, string>> = {
  auto: { es: "Auto", en: "Car", pt: "Carro", ko: "자동차" },
  metro: { es: "Metro", en: "Metro", pt: "Metrô", ko: "지하철" },
  bus: { es: "Bus", en: "Bus", pt: "Ônibus", ko: "버스" },
  bicicleta: { es: "Bicicleta", en: "Bicycle", pt: "Bicicleta", ko: "자전거" },
  caminando: { es: "Caminando", en: "Walking", pt: "Caminhando", ko: "도보" },
  app_transporte: { es: "App de transporte", en: "Ride-hailing app", pt: "Aplicativo de transporte", ko: "차량 호출 앱" },
  otro: { es: "Otro", en: "Other", pt: "Outro", ko: "기타" },
};

const ERROR_TRANSLATIONS: Record<string, Record<PublicFormLanguage, string>> = {
  "Campo no reconocido": { es: "Campo no reconocido", en: "Unknown field", pt: "Campo não reconhecido", ko: "알 수 없는 필드입니다" },
  "Este campo es obligatorio": { es: "Este campo es obligatorio", en: "This field is required", pt: "Este campo é obrigatório", ko: "필수 입력 항목입니다" },
  "Correo inválido": { es: "Correo inválido", en: "Invalid email address", pt: "E-mail inválido", ko: "유효하지 않은 이메일입니다" },
  "Teléfono inválido": { es: "Teléfono inválido", en: "Invalid phone number", pt: "Telefone inválido", ko: "유효하지 않은 전화번호입니다" },
  "Debe seleccionar una opción válida": { es: "Debe seleccionar una opción válida", en: "Please select a valid option", pt: "Selecione uma opção válida", ko: "유효한 옵션을 선택하세요" },
  "Debe seleccionar una o más opciones válidas": { es: "Debe seleccionar una o más opciones válidas", en: "Please select one or more valid options", pt: "Selecione uma ou mais opções válidas", ko: "하나 이상의 유효한 옵션을 선택하세요" },
  "Debe ser verdadero o falso": { es: "Debe ser verdadero o falso", en: "The value must be true or false", pt: "O valor deve ser verdadeiro ou falso", ko: "값은 참 또는 거짓이어야 합니다" },
  "Valor inválido": { es: "Valor inválido", en: "Invalid value", pt: "Valor inválido", ko: "유효하지 않은 값입니다" },
};

export function normalizePublicFormLanguage(language?: string | null): PublicFormLanguage {
  return language === "en" || language === "pt" || language === "ko" ? language : "es";
}

export function publicFormCopy(language?: string | null): PublicFormCopy {
  return COPY[normalizePublicFormLanguage(language)];
}

export function publicFormFieldLabel(fieldKey: string, currentLabel: string, language?: string | null): string {
  const lang = normalizePublicFormLanguage(language);
  return FIELD_LABELS[fieldKey]?.[lang] ?? currentLabel;
}

export function publicFormOptionLabel(value: string, currentLabel: string, language?: string | null): string {
  const lang = normalizePublicFormLanguage(language);
  return OPTION_LABELS[value]?.[lang] ?? currentLabel;
}

export function translatePublicFormError(message: string, language?: string | null): string {
  const lang = normalizePublicFormLanguage(language);
  const direct = ERROR_TRANSLATIONS[message]?.[lang];
  if (direct) return direct;

  const maxLength = message.match(/^Debe tener máximo (\d+) caracteres$/);
  if (maxLength) {
    const count = maxLength[1];
    if (lang === "en") return `Must be at most ${count} characters`;
    if (lang === "pt") return `Deve ter no máximo ${count} caracteres`;
    if (lang === "ko") return `최대 ${count}자까지 입력할 수 있습니다`;
  }

  return message;
}
