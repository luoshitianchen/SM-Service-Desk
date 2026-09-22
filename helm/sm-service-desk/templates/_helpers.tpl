{{/*
通用辅助模板：名称/全名/标签选择器
*/}}
{{- define "sm-service-desk.name" -}}
{{ default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "sm-service-desk.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end -}}
{{- end }}

{{- define "sm-service-desk.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end }}

{{- define "sm-service-desk.commonLabels" -}}
app.kubernetes.io/name: {{ include "sm-service-desk.name" . }}
helm.sh/chart: {{ include "sm-service-desk.chart" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "sm-service-desk.selectorLabels" -}}
app.kubernetes.io/name: {{ include "sm-service-desk.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "sm-service-desk.serviceAccountName" -}}
{{ default (printf "%s-sa" (include "sm-service-desk.fullname" .)) .Values.serviceAccount.name }}
{{- end }}
