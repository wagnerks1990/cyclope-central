package service

import (
	"context"
	"log/slog"
)

type WorkFunc func(context.Context) error

type Runner struct {
	logger *slog.Logger
	work   WorkFunc
}

func NewRunner(logger *slog.Logger, work WorkFunc) *Runner {
	return &Runner{logger: logger, work: work}
}

func (r *Runner) Run(ctx context.Context) error {
	r.logger.Info("starting Cyclope Central agent service runner")
	return r.work(ctx)
}
